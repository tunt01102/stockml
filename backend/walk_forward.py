"""
walk_forward.py
---------------
Đánh giá walk-forward (expanding window) — chuẩn vàng cho chuỗi thời gian
tài chính, thay vì 1 lần train/test split.

Quy trình:
  - Huấn luyện trên [0 : t], dự đoán khối [t : t+step], cuốn t tiến lên.
  - Gom toàn bộ dự đoán out-of-sample -> tính metric trên đó.
  - LUÔN so với baseline ngây thơ (random walk: dự báo lợi suất tương lai = 0)
    để biết ML có thực sự thêm giá trị hay không.

Metric:
  - RMSE / R2 : sai số thống kê
  - Directional Accuracy : tỉ lệ đoán ĐÚNG HƯỚNG (kinh tế quan trọng hơn RMSE)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional

import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error, r2_score

from financial_regression import ModelSpec, RegressionModel, ModelFactory


@dataclass
class WFResult:
    model_name: str
    rmse: float
    r2_oos: float
    directional_acc: float
    n_predictions: int
    fold_rmses: List[float] = field(default_factory=list)

    def as_row(self) -> dict:
        return {
            "Model": self.model_name,
            "OOS_RMSE": round(self.rmse, 5),
            "OOS_R2": round(self.r2_oos, 4),
            "Direction_Acc": round(self.directional_acc, 4),
            "N_pred": self.n_predictions,
            "fold_rmses": [round(v, 5) for v in self.fold_rmses],
        }


class WalkForwardEvaluator:
    def __init__(self, initial_train: int = 500, step: int = 20):
        # initial_train: số phiên tối thiểu để bắt đầu; step: nhịp cuốn
        self.initial_train = initial_train
        self.step = step

    def total_folds(self, n: int) -> int:
        """Tổng số folds với n mẫu."""
        return max(1, (n - self.initial_train + self.step - 1) // self.step)

    def _run_one(
        self,
        spec: ModelSpec,
        X: pd.DataFrame,
        y: pd.Series,
        on_fold: Optional[Callable[[int, float], None]] = None,
    ) -> WFResult:
        """Chạy walk-forward cho 1 mô hình.

        on_fold(fold_index, fold_rmse): callback gọi sau mỗi fold,
        dùng để emit progress events trong SSE stream.
        """
        preds, actuals = [], []
        fold_rmses: List[float] = []
        n = len(X)
        t = self.initial_train
        fold_idx = 0

        while t < n:
            end = min(t + self.step, n)

            # tạo mô hình mới mỗi vòng -> không nhớ tương lai
            model = RegressionModel(spec)
            # scaler cũng chỉ fit trên quá khứ
            model.fit(X.iloc[:t], y.iloc[:t])

            fold_preds = model.predict(X.iloc[t:end])
            fold_actual = y.iloc[t:end].values

            preds.extend(fold_preds)
            actuals.extend(fold_actual)

            fold_rmse = float(np.sqrt(mean_squared_error(fold_actual, fold_preds)))
            fold_rmses.append(fold_rmse)

            if on_fold is not None:
                on_fold(fold_idx, fold_rmse)

            t = end
            fold_idx += 1

        preds_arr = np.array(preds)
        actuals_arr = np.array(actuals)

        return WFResult(
            model_name=spec.name,
            rmse=float(np.sqrt(mean_squared_error(actuals_arr, preds_arr))),
            r2_oos=float(r2_score(actuals_arr, preds_arr)),
            directional_acc=float(np.mean(np.sign(preds_arr) == np.sign(actuals_arr))),
            n_predictions=len(preds_arr),
            fold_rmses=fold_rmses,
        )

    def naive_baseline(self, y: pd.Series) -> WFResult:
        """Random walk: dự báo lợi suất tương lai = 0 (giá ngày mai = hôm nay)."""
        actuals = y.iloc[self.initial_train:].values
        preds = np.zeros_like(actuals)
        dir_acc = float(np.mean(np.sign(actuals) == 0))
        return WFResult(
            model_name="Naive (random walk)",
            rmse=float(np.sqrt(mean_squared_error(actuals, preds))),
            r2_oos=float(r2_score(actuals, preds)),
            directional_acc=dir_acc,
            n_predictions=len(actuals),
            fold_rmses=[],
        )

    def run_all(self, specs: List[ModelSpec], X, y) -> pd.DataFrame:
        rows = [self.naive_baseline(y).as_row()]
        for spec in specs:
            rows.append(self._run_one(spec, X, y).as_row())
        # fold_rmses là list — drop trước khi tạo DataFrame
        df_rows = [{k: v for k, v in r.items() if k != "fold_rmses"} for r in rows]
        return pd.DataFrame(df_rows).sort_values("OOS_RMSE").reset_index(drop=True)
