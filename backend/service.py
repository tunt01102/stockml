"""
service.py
----------
Tầng dịch vụ: điều phối fetch -> feature engineering -> walk-forward,
đóng gói kết quả thành dict JSON-serializable cho API.

Hai interface:
  analyze()        -> dict đầy đủ (sync, dùng cho REST POST)
  analyze_stream() -> generator yield SSE events theo từng giai đoạn
                      (sync generator + threading, dùng cho SSE GET)
"""

from __future__ import annotations

import queue
import threading
import time
from typing import Generator, Optional

import numpy as np
import pandas as pd

from providers import DataProvider, SyntheticProvider, get_provider
from feature_engineering import FeatureBuilder
from walk_forward import WalkForwardEvaluator
from financial_regression import ModelFactory, RegressionModel


class AnalysisService:
    def __init__(self):
        self.real_provider = get_provider(prefer_real=True)
        self.synthetic = SyntheticProvider()

    def _fetch_with_fallback(self, symbol, start, end):
        """Thử nguồn thật; nếu lỗi -> synthetic, gắn cờ."""
        try:
            df = self.real_provider.fetch(symbol, start, end)
            if df is None or len(df) < 120:
                raise ValueError("Ít dữ liệu")
            return df, self.real_provider.name
        except Exception:
            return self.synthetic.fetch(symbol, start, end), "synthetic_fallback"

    def _build_result(self, symbol, source, horizon, df, X, y, rows, baseline, best_spec, initial_train) -> dict:
        """Đóng gói dict kết quả JSON-serializable."""
        scatter = self._scatter_for(best_spec, X, y, initial_train)

        price = df[["date", "close"]].copy()
        price["date"] = price["date"].dt.strftime("%Y-%m-%d")
        stride = max(1, len(price) // 600)
        price_series = price.iloc[::stride].to_dict("records")

        models_sorted = sorted(rows, key=lambda r: r["OOS_RMSE"])
        beats_baseline = any(
            r["OOS_RMSE"] < baseline["OOS_RMSE"] and r["Model"] != baseline["Model"]
            for r in rows
        )

        return {
            "symbol": symbol.upper(),
            "source": source,
            "horizon": horizon,
            "n_obs": len(X),
            "date_range": [price.iloc[0]["date"], price.iloc[-1]["date"]],
            "target_mean": round(float(y.mean()), 5),
            "target_std": round(float(y.std()), 5),
            "baseline_rmse": baseline["OOS_RMSE"],
            "best_model": best_spec.name,
            "beats_baseline": bool(beats_baseline),
            "models": models_sorted,
            "price_series": price_series,
            "scatter": scatter,
        }

    def analyze(self, symbol: str, start: str, end: str, horizon: int = 5) -> dict:
        """Phân tích đồng bộ — trả dict JSON đầy đủ."""
        df, source = self._fetch_with_fallback(symbol, start, end)

        builder = FeatureBuilder(horizon=horizon)
        X, y = builder.build(df)
        n = len(X)
        if n < 200:
            raise ValueError(f"Không đủ dữ liệu sau feature engineering (n={n}).")

        initial_train = min(500, int(n * 0.5))
        evaluator = WalkForwardEvaluator(initial_train=initial_train, step=40)

        rows = []
        baseline = evaluator.naive_baseline(y).as_row()
        rows.append(baseline)

        best_spec, best_rmse = None, np.inf
        for spec in ModelFactory.fast_default():
            res = evaluator._run_one(spec, X, y)
            rows.append(res.as_row())
            if res.rmse < best_rmse:
                best_rmse, best_spec = res.rmse, spec

        return self._build_result(symbol, source, horizon, df, X, y, rows, baseline, best_spec, initial_train)

    def analyze_stream(self, symbol: str, start: str, end: str, horizon: int = 5) -> Generator[dict, None, None]:
        """Generator yield SSE events — mỗi giai đoạn ML là 1 cụm events.

        Dùng threading.Queue: worker thread chạy ML và đưa events vào queue,
        generator đọc từ queue và yield ra ngoài.
        """
        q: queue.Queue = queue.Queue()
        SENTINEL = object()

        def worker():
            try:
                # ── Giai đoạn 1: Tải dữ liệu ──────────────────────────────
                years = list(range(int(start[:4]), int(end[:4]) + 1))
                q.put({"stage": "fetch_start", "years": years, "total": len(years)})

                df, source = self._fetch_with_fallback(symbol, start, end)

                # Emit từng năm một (visual feedback — dữ liệu đã load xong)
                for i, yr in enumerate(years):
                    q.put({
                        "stage": "fetch_year",
                        "year": yr,
                        "done": i + 1,
                        "total": len(years),
                    })
                    time.sleep(0.06)  # delay nhỏ để animation năm chạy rõ

                # ── Giai đoạn 2: Kiểm tra dữ liệu ─────────────────────────
                q.put({
                    "stage": "validate",
                    "rows": len(df),
                    "cols": int(df.shape[1]),
                    "source": source,
                    "date_start": str(df["date"].iloc[0].date()),
                    "date_end": str(df["date"].iloc[-1].date()),
                    "has_nan": int(df.isnull().sum().sum()),
                })

                # ── Giai đoạn 3: Feature Engineering ──────────────────────
                q.put({"stage": "features_start"})
                builder = FeatureBuilder(horizon=horizon)
                X, y = builder.build(df)
                n = len(X)

                if n < 200:
                    raise ValueError(f"Không đủ dữ liệu sau feature engineering (n={n}).")

                q.put({
                    "stage": "features_done",
                    "n_features": int(X.shape[1]),
                    "n_samples": n,
                    "feature_names": list(X.columns),
                    "dropped_rows": len(df) - n,
                })

                # ── Giai đoạn 4: Walk-Forward Evaluation ───────────────────
                initial_train = min(500, int(n * 0.5))
                evaluator = WalkForwardEvaluator(initial_train=initial_train, step=40)
                total_folds = evaluator.total_folds(n)

                specs = ModelFactory.fast_default()
                q.put({
                    "stage": "training_start",
                    "models": [s.name for s in specs],
                    "total_folds": total_folds,
                    "initial_train": initial_train,
                })

                rows = []
                baseline = evaluator.naive_baseline(y).as_row()
                rows.append(baseline)

                best_spec, best_rmse = None, np.inf

                for spec in specs:
                    q.put({
                        "stage": "model_start",
                        "model": spec.name,
                        "total_folds": total_folds,
                        "needs_scaling": spec.needs_scaling,
                    })

                    def on_fold(fold_i: int, fold_rmse: float, _name: str = spec.name) -> None:
                        q.put({
                            "stage": "model_fold",
                            "model": _name,
                            "fold": fold_i + 1,
                            "total_folds": total_folds,
                            "fold_rmse": round(float(fold_rmse), 5),
                        })

                    res = evaluator._run_one(spec, X, y, on_fold=on_fold)
                    row = res.as_row()
                    rows.append(row)

                    if res.rmse < best_rmse:
                        best_rmse, best_spec = res.rmse, spec

                    q.put({
                        "stage": "model_done",
                        "model": spec.name,
                        "oos_rmse": row["OOS_RMSE"],
                        "oos_r2": row["OOS_R2"],
                        "direction_acc": row["Direction_Acc"],
                        "n_pred": row["N_pred"],
                        "fold_rmses": row["fold_rmses"],
                        "beats_baseline": row["OOS_RMSE"] < baseline["OOS_RMSE"],
                    })

                # ── Giai đoạn 5: Kết quả cuối ──────────────────────────────
                result = self._build_result(
                    symbol, source, horizon, df, X, y, rows, baseline, best_spec, initial_train
                )
                q.put({"stage": "complete", "result": result})

            except Exception as exc:
                q.put({"stage": "error", "message": str(exc)})
            finally:
                q.put(SENTINEL)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

        while True:
            event = q.get()
            if event is SENTINEL:
                break
            yield event

    def _scatter_for(self, spec, X, y, initial_train, sample=250):
        model = RegressionModel(spec)
        model.fit(X.iloc[:initial_train], y.iloc[:initial_train])
        preds = model.predict(X.iloc[initial_train:])
        actual = y.iloc[initial_train:].values
        idx = np.linspace(0, len(preds) - 1, min(sample, len(preds))).astype(int)
        return [{"actual": round(float(actual[i]), 5),
                 "pred": round(float(preds[i]), 5)} for i in idx]
