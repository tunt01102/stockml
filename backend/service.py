"""
service.py
----------
Tầng dịch vụ: điều phối fetch -> fundamental -> feature engineering -> walk-forward,
đóng gói kết quả thành dict JSON-serializable cho API.

Hai interface:
  analyze()        -> dict đầy đủ (sync, dùng cho REST POST)
  analyze_stream() -> generator yield SSE events theo từng giai đoạn
                      (sync generator + threading, dùng cho SSE GET)

mode="return"     : dự báo lợi suất — baseline = naive random walk
mode="volatility" : dự báo biến động — baseline = GARCH(1,1)
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
from fundamental_providers import FundamentalProvider


class AnalysisService:
    def __init__(self):
        self.real_provider = get_provider(prefer_real=True)
        self.synthetic = SyntheticProvider()
        self.fundamental = FundamentalProvider()

    def _fetch_with_fallback(self, symbol, start, end):
        """Thử nguồn thật; nếu lỗi -> synthetic, gắn cờ."""
        try:
            df = self.real_provider.fetch(symbol, start, end)
            if df is None or len(df) < 120:
                raise ValueError("Ít dữ liệu")
            return df, self.real_provider.name
        except Exception:
            return self.synthetic.fetch(symbol, start, end), "synthetic_fallback"

    def _fetch_fundamental(self, symbol, start, end):
        """Tải dữ liệu cơ bản (P/E, P/B, nguyên liệu). Trả None nếu thất bại."""
        try:
            ratios = self.fundamental.fetch_vnstock_ratios(symbol, start, end)
            commodities = self.fundamental.fetch_commodity(start, end)

            parts = [df for df in [ratios, commodities] if df is not None and not df.empty]
            if not parts:
                return None

            if len(parts) == 1:
                return parts[0]

            merged = parts[0].join(parts[1], how="outer")
            return merged
        except Exception:
            return None

    def _build_result(
        self, symbol, source, horizon, mode, price_type, df, X, y, rows, baseline, best_spec, initial_train
    ) -> dict:
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
            "mode": mode,
            "price_type": price_type,
            "n_obs": len(X),
            "date_range": [price.iloc[0]["date"], price.iloc[-1]["date"]],
            "target_mean": round(float(y.mean()), 5),
            "target_std": round(float(y.std()), 5),
            "baseline_rmse": baseline["OOS_RMSE"],
            "baseline_name": baseline["Model"],
            "best_model": best_spec.name if best_spec else "",
            "beats_baseline": bool(beats_baseline),
            "models": models_sorted,
            "price_series": price_series,
            "scatter": scatter,
            "feature_names": list(X.columns),
        }

    def analyze(
        self, symbol: str, start: str, end: str, horizon: int = 5, mode: str = "return",
        price_type: str = "close",
    ) -> dict:
        """Phân tích đồng bộ — trả dict JSON đầy đủ."""
        df, source = self._fetch_with_fallback(symbol, start, end)
        fundamental_df = self._fetch_fundamental(symbol, start, end)

        builder = FeatureBuilder(horizon=horizon, mode=mode, price_type=price_type)
        X, y = builder.build(df, fundamental_df=fundamental_df)
        n = len(X)
        if n < 200:
            raise ValueError(f"Không đủ dữ liệu sau feature engineering (n={n}).")

        initial_train = min(500, int(n * 0.5))
        evaluator = WalkForwardEvaluator(initial_train=initial_train, step=40)

        rows = []

        if mode == "volatility":
            garch_spec = ModelFactory.garch_baseline(horizon=horizon)
            garch_res = evaluator._run_one(garch_spec, X, y)
            baseline = garch_res.as_row()
            rows.append(baseline)
        else:
            baseline = evaluator.naive_baseline(y).as_row()
            rows.append(baseline)

        best_spec, best_rmse = None, np.inf
        for spec in ModelFactory.fast_default():
            res = evaluator._run_one(spec, X, y)
            rows.append(res.as_row())
            if res.rmse < best_rmse:
                best_rmse, best_spec = res.rmse, spec

        return self._build_result(
            symbol, source, horizon, mode, price_type, df, X, y, rows, baseline, best_spec, initial_train
        )

    def analyze_stream(
        self, symbol: str, start: str, end: str, horizon: int = 5, mode: str = "return",
        price_type: str = "close",
    ) -> Generator[dict, None, None]:
        """Generator yield SSE events — mỗi giai đoạn ML là 1 cụm events."""
        q: queue.Queue = queue.Queue()
        SENTINEL = object()

        def worker():
            try:
                # ── Giai đoạn 1: Tải dữ liệu ──────────────────────────────
                years = list(range(int(start[:4]), int(end[:4]) + 1))
                q.put({"stage": "fetch_start", "years": years, "total": len(years)})

                df, source = self._fetch_with_fallback(symbol, start, end)

                for i, yr in enumerate(years):
                    q.put({
                        "stage": "fetch_year",
                        "year": yr,
                        "done": i + 1,
                        "total": len(years),
                    })
                    time.sleep(0.06)

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

                # ── Giai đoạn 2b: Dữ liệu cơ bản ─────────────────────────
                q.put({"stage": "fundamental_start"})
                fundamental_df = self._fetch_fundamental(symbol, start, end)
                fund_cols = list(fundamental_df.columns) if fundamental_df is not None else []
                q.put({"stage": "fundamental_done", "cols": fund_cols})

                # ── Giai đoạn 3: Feature Engineering ──────────────────────
                q.put({"stage": "features_start"})
                builder = FeatureBuilder(horizon=horizon, mode=mode, price_type=price_type)
                X, y = builder.build(df, fundamental_df=fundamental_df)
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

                ml_specs = ModelFactory.fast_default()

                if mode == "volatility":
                    garch_spec = ModelFactory.garch_baseline(horizon=horizon)
                    all_model_names = [garch_spec.name] + [s.name for s in ml_specs]
                else:
                    garch_spec = None
                    all_model_names = [s.name for s in ml_specs]

                q.put({
                    "stage": "training_start",
                    "models": all_model_names,
                    "total_folds": total_folds,
                    "initial_train": initial_train,
                })

                rows = []
                baseline = None

                # GARCH baseline (volatility mode only)
                if mode == "volatility" and garch_spec is not None:
                    q.put({
                        "stage": "model_start",
                        "model": garch_spec.name,
                        "total_folds": total_folds,
                        "needs_scaling": garch_spec.needs_scaling,
                    })

                    def on_garch_fold(fold_i: int, fold_rmse: float) -> None:
                        q.put({
                            "stage": "model_fold",
                            "model": garch_spec.name,
                            "fold": fold_i + 1,
                            "total_folds": total_folds,
                            "fold_rmse": round(float(fold_rmse), 5),
                        })

                    garch_res = evaluator._run_one(garch_spec, X, y, on_fold=on_garch_fold)
                    baseline = garch_res.as_row()
                    rows.append(baseline)
                    q.put({
                        "stage": "model_done",
                        "model": garch_spec.name,
                        "oos_rmse": baseline["OOS_RMSE"],
                        "oos_r2": baseline["OOS_R2"],
                        "direction_acc": baseline["Direction_Acc"],
                        "n_pred": baseline["N_pred"],
                        "fold_rmses": baseline["fold_rmses"],
                        "beats_baseline": False,
                    })
                else:
                    baseline = evaluator.naive_baseline(y).as_row()
                    rows.append(baseline)

                best_spec, best_rmse = None, np.inf

                for spec in ml_specs:
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
                    symbol, source, horizon, mode, price_type, df, X, y, rows, baseline, best_spec, initial_train
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
        if spec is None:
            return []
        model = RegressionModel(spec)
        model.fit(X.iloc[:initial_train], y.iloc[:initial_train])
        preds = model.predict(X.iloc[initial_train:])
        actual = y.iloc[initial_train:].values
        idx = np.linspace(0, len(preds) - 1, min(sample, len(preds))).astype(int)
        return [{"actual": round(float(actual[i]), 5),
                 "pred": round(float(preds[i]), 5)} for i in idx]
