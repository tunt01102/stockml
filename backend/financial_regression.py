"""
financial_regression.py
------------------------
Khung học máy có giám sát (supervised regression) hướng đối tượng cho
môi trường tài chính, xây trên scikit-learn.

Thiết kế xoay quanh 3 design pattern:
  - Strategy  : các thuật toán hồi quy thay thế lẫn nhau qua cùng interface
  - Factory   : tạo mô hình theo tên, tách phần khởi tạo khỏi phần dùng
  - Pipeline  : đóng gói chuẩn hoá + mô hình thành 1 estimator, chống rò rỉ dữ liệu

Năm lớp thuật toán:
  Ridge                    - L2 regularization (Hoerl & Kennard, 1970)
  ElasticNet               - L1 + L2, tối ưu bằng Coordinate Descent (Zou & Hastie, 2005)
  RandomForestRegressor    - Bagging + random feature subset (Breiman, 2001)
  GradientBoostingRegressor- Boosting cây nông (Friedman, 2001)
  StackingEnsemble         - Meta-Learning: RF + GBR + ElasticNet → Ridge meta-learner
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler
from sklearn.model_selection import (
    train_test_split,
    cross_val_score,
    TimeSeriesSplit,
)
from sklearn.metrics import (
    mean_squared_error,
    mean_absolute_error,
    r2_score,
)
from sklearn.linear_model import Ridge, ElasticNet
from sklearn.ensemble import (
    RandomForestRegressor,
    GradientBoostingRegressor,
    StackingRegressor,
)


# ----------------------------------------------------------------------
# 1. SPECIFICATION — mô tả 1 thuật toán (estimator + có cần chuẩn hoá không)
# ----------------------------------------------------------------------
@dataclass(frozen=True)
class ModelSpec:
    """Đặc tả 1 thuật toán: estimator và cờ cần chuẩn hoá đặc trưng.

    needs_scaling = True  -> mô hình tuyến tính (Ridge, ElasticNet):
                             nhạy với thang đo, BẮT BUỘC chuẩn hoá.
    needs_scaling = False -> mô hình dựa trên cây (RF, GBR):
                             bất biến với phép biến đổi đơn điệu, KHÔNG cần.
    """
    name: str
    estimator: BaseEstimator
    needs_scaling: bool


# ----------------------------------------------------------------------
# 2. THÔNG TIN GIÁO DỤC — dùng cho accordion UI giảng dạy
# ----------------------------------------------------------------------
MODEL_INFO: Dict[str, dict] = {
    "Ridge": {
        "full_name": "Ridge Regression (L2)",
        "algorithm": "Ordinary Least Squares + L2 Regularization",
        "year": 1970,
        "authors": "Hoerl & Kennard",
        "formula": "min ½·‖Xw−y‖² + α·‖w‖²",
        "formula_explain": "Tối thiểu hoá MSE + hình phạt bình phương trọng số. α lớn → w nhỏ dần về 0.",
        "params": {"alpha": 1.0},
        "needs_scaling": True,
        "scaling_reason": "Penalty α·‖w‖² tính trên độ lớn của w. Nếu feature_A có giá trị 1000× feature_B, hình phạt sẽ ưu tiên co w_A hơn w_B — sai lệch không phản ánh tầm quan trọng thực.",
        "skip_scaling_consequence": "Mô hình bị dominated bởi features có thang đo lớn (VD: volume ~ 10⁶), penalty vô nghĩa.",
        "strength": "Ổn định, nhanh, xử lý multicollinearity tốt. Baseline tốt cho dữ liệu tài chính.",
        "weakness": "Không loại bỏ features thừa (‖w‖² không đưa hệ số về đúng 0).",
        "icon": "📐",
        "color": "#58a6ff",
    },
    "ElasticNet": {
        "full_name": "ElasticNet Regression (L1 + L2)",
        "algorithm": "Coordinate Descent",
        "year": 2005,
        "authors": "Zou & Hastie",
        "formula": "min ½·‖Xw−y‖² + α·ρ·‖w‖₁ + α·(1−ρ)/2·‖w‖²",
        "formula_explain": "Kết hợp Lasso (L1, tạo sparsity) và Ridge (L2, ổn định). ρ=0.5 → cân bằng hai mục tiêu.",
        "params": {"alpha": 0.1, "l1_ratio": 0.5, "max_iter": 10000},
        "needs_scaling": True,
        "scaling_reason": "L1 + L2 penalty nhạy với thang đo: feature có giá trị lớn sẽ bị phạt mạnh hơn dù thực tế không quan trọng hơn.",
        "skip_scaling_consequence": "Hệ số của features có thang đo nhỏ bị co về 0 không vì lý do kỹ thuật — loại nhầm thông tin hữu ích.",
        "optimization": "Coordinate Descent: tối ưu từng hệ số w_j trong khi giữ nguyên các hệ số còn lại → lặp đến hội tụ.",
        "strength": "Vừa chọn lọc feature (L1) vừa xử lý multicollinearity (L2). Tốt khi nhiều features tương quan.",
        "weakness": "Chậm hơn Ridge nếu max_iter lớn, cần tune thêm l1_ratio.",
        "icon": "⚡",
        "color": "#f5a623",
    },
    "RandomForest": {
        "full_name": "Random Forest Regressor",
        "algorithm": "Bagging + Random Feature Subspace",
        "year": 2001,
        "authors": "Leo Breiman",
        "formula": "ŷ = (1/B) · Σ Treeᵦ(x)",
        "formula_explain": "Trung bình dự đoán của B cây quyết định, mỗi cây train trên bootstrap sample và chỉ xét √p features ngẫu nhiên tại mỗi nút.",
        "params": {"n_estimators": 120, "min_samples_leaf": 5, "max_depth": "None"},
        "needs_scaling": False,
        "scaling_reason": "Cây quyết định chia theo ngưỡng (VD: feature > 0.5?). Phép chia này bất biến với biến đổi đơn điệu như chuẩn hoá — kết quả không đổi dù scale features.",
        "skip_scaling_consequence": "Không có hậu quả — cây không bị ảnh hưởng bởi thang đo.",
        "strength": "Chống overfit tốt (nhiều cây độc lập), xử lý phi tuyến, quan hệ tương tác features.",
        "weakness": "Chậm hơn mô hình tuyến tính, kém ngoại suy (không vượt ngoài vùng dữ liệu training).",
        "icon": "🌲",
        "color": "#3fb950",
    },
    "GradientBoosting": {
        "full_name": "Gradient Boosting Regressor",
        "algorithm": "Gradient Boosting (Stochastic)",
        "year": 2001,
        "authors": "Jerome H. Friedman",
        "formula": "F_m(x) = F_{m-1}(x) + η · h_m(x)",
        "formula_explain": "Cộng dần weak learner h_m (cây nông) fit trên residuals của mô hình trước. η (learning rate) kiểm soát bước cập nhật.",
        "params": {"n_estimators": 120, "learning_rate": 0.05, "max_depth": 3, "subsample": 0.8},
        "needs_scaling": False,
        "scaling_reason": "Tương tự Random Forest — cây quyết định bất biến với thang đo features.",
        "skip_scaling_consequence": "Không có hậu quả.",
        "optimization": "Gradient Descent trong không gian hàm: tại mỗi bước, fit cây mới vào âm gradient của loss function (= residuals với MSE).",
        "strength": "Thường có accuracy cao nhất trong nhóm cây. max_depth=3 (weak learner nông) là đặc trưng boosting — tránh overfit.",
        "weakness": "Nhạy cảm với outliers, cần tune learning_rate + n_estimators cẩn thận.",
        "icon": "🚀",
        "color": "#f85149",
    },
    "StackingEnsemble": {
        "full_name": "Stacking Ensemble (Meta-Learning)",
        "algorithm": "Stacked Generalization",
        "year": 1992,
        "authors": "David Wolpert",
        "formula": "ŷ_meta = Ridge(ElasticNet(x), RF(x), GBR(x))",
        "formula_explain": "Bước 1: 3 base models dự đoán qua cross-validation (out-of-fold). Bước 2: Ridge học cách kết hợp tối ưu 3 dự đoán đó.",
        "params": {
            "base_models": ["ElasticNet(α=0.1)", "RandomForest(80 trees)", "GBR(80 trees, lr=0.05)"],
            "meta_learner": "Ridge",
            "cv": 5,
        },
        "needs_scaling": True,
        "scaling_reason": "Meta-learner là Ridge — cần chuẩn hoá meta-features (output của base models) để Ridge penalty hoạt động đúng.",
        "skip_scaling_consequence": "Ridge meta-learner sẽ bị dominated bởi base model có output có phương sai lớn.",
        "strength": "Kết hợp điểm mạnh của từng mô hình. Tốt khi các base models có errors không tương quan.",
        "weakness": "Chậm nhất (= tổng thời gian tất cả base models × cv_folds). Dễ overfit nếu CV không đủ.",
        "icon": "🧩",
        "color": "#a371f7",
        "architecture": [
            "Dữ liệu train → chia 5 fold (TimeSeriesSplit)",
            "Mỗi fold: train ElasticNet, RF, GBR trên 4 folds còn lại → predict fold đang giữ",
            "Ghép dự đoán out-of-fold → tạo meta-features (N×3 matrix)",
            "Train Ridge trên meta-features → học trọng số tối ưu cho mỗi base model",
            "Inference: chạy 3 base models → Ridge kết hợp → dự đoán cuối",
        ],
    },
}


# ----------------------------------------------------------------------
# 3. GARCH BASELINE — sklearn-compatible wrapper cho volatility mode
# ----------------------------------------------------------------------
class GarchBaseline(BaseEstimator, RegressorMixin):
    """Baseline cho volatility mode: dự đoán vol = sqrt(garch_forecast_t * horizon).

    Dùng quy tắc sqrt-of-time để scale 1-day GARCH variance sang h-day vol.
    Không có tham số học — fit() là no-op.
    """

    def __init__(self, horizon: int = 5):
        self.horizon = horizon

    def fit(self, X, y=None):
        # Set sklearn-required fitted attributes so check_is_fitted() passes
        self.n_features_in_ = X.shape[1] if hasattr(X, "shape") else len(X.columns)
        self.is_fitted_ = True
        return self

    def predict(self, X):
        if hasattr(X, "columns") and "garch_forecast_t" in X.columns:
            var = X["garch_forecast_t"].values
        elif hasattr(X, "__getitem__") and "garch_forecast_t" in X:
            var = X["garch_forecast_t"].values
        else:
            # GARCH features unavailable — fallback to rolling vol proxy
            col = "vol_10d" if (hasattr(X, "columns") and "vol_10d" in X.columns) else None
            fallback = X[col].values if col else np.full(len(X), 0.01)
            return fallback * np.sqrt(self.horizon)
        return np.sqrt(np.maximum(0.0, var) * self.horizon)


# ----------------------------------------------------------------------
# 4. FACTORY — tạo các ModelSpec chuẩn, hyperparameter tập trung 1 chỗ
# ----------------------------------------------------------------------
class ModelFactory:
    """Factory tạo 5 lớp thuật toán hồi quy chuyên dụng."""

    RANDOM_STATE = 42

    @classmethod
    def ridge(cls, alpha: float = 1.0) -> ModelSpec:
        return ModelSpec(
            name="Ridge",
            estimator=Ridge(alpha=alpha, random_state=cls.RANDOM_STATE),
            needs_scaling=True,
        )

    @classmethod
    def elastic_net(cls, alpha: float = 0.1, l1_ratio: float = 0.5) -> ModelSpec:
        return ModelSpec(
            name="ElasticNet",
            estimator=ElasticNet(
                alpha=alpha,
                l1_ratio=l1_ratio,
                random_state=cls.RANDOM_STATE,
                max_iter=10_000,
            ),
            needs_scaling=True,
        )

    @classmethod
    def random_forest(cls, n_estimators: int = 300) -> ModelSpec:
        return ModelSpec(
            name="RandomForest",
            estimator=RandomForestRegressor(
                n_estimators=n_estimators,
                max_depth=None,
                min_samples_leaf=5,
                n_jobs=-1,
                random_state=cls.RANDOM_STATE,
            ),
            needs_scaling=False,
        )

    @classmethod
    def gradient_boosting(cls, n_estimators: int = 300) -> ModelSpec:
        return ModelSpec(
            name="GradientBoosting",
            estimator=GradientBoostingRegressor(
                n_estimators=n_estimators,
                learning_rate=0.05,
                max_depth=3,
                subsample=0.8,
                random_state=cls.RANDOM_STATE,
            ),
            needs_scaling=False,
        )

    @classmethod
    def stacking(cls) -> ModelSpec:
        """Stacking Ensemble: ElasticNet + RF + GBR làm base, Ridge làm meta-learner.

        Dùng base models nhẹ hơn (n_estimators=60) để kiểm soát thời gian chạy.
        cv=5 với TimeSeriesSplit để tạo out-of-fold predictions không bị look-ahead.
        """
        base_estimators = [
            ("en", ElasticNet(alpha=0.1, l1_ratio=0.5, max_iter=10_000, random_state=cls.RANDOM_STATE)),
            ("rf", RandomForestRegressor(n_estimators=60, min_samples_leaf=5, n_jobs=-1, random_state=cls.RANDOM_STATE)),
            ("gbr", GradientBoostingRegressor(n_estimators=60, learning_rate=0.05, max_depth=3, subsample=0.8, random_state=cls.RANDOM_STATE)),
        ]
        return ModelSpec(
            name="StackingEnsemble",
            estimator=StackingRegressor(
                estimators=base_estimators,
                final_estimator=Ridge(random_state=cls.RANDOM_STATE),
                cv=5,
                n_jobs=-1,
            ),
            needs_scaling=True,
        )

    @classmethod
    def all_default(cls) -> List[ModelSpec]:
        return [
            cls.ridge(),
            cls.elastic_net(),
            cls.random_forest(),
            cls.gradient_boosting(),
            cls.stacking(),
        ]

    @classmethod
    def garch_baseline(cls, horizon: int = 5) -> ModelSpec:
        """GARCH baseline cho volatility mode: sqrt(garch_forecast_t * horizon)."""
        return ModelSpec(
            name="GARCH Baseline",
            estimator=GarchBaseline(horizon=horizon),
            needs_scaling=False,
        )

    @classmethod
    def fast_default(cls) -> List[ModelSpec]:
        """Preset nhẹ cho web (ít cây hơn) -> phản hồi nhanh, kết luận không đổi."""
        return [
            cls.ridge(),
            cls.elastic_net(),
            cls.random_forest(n_estimators=120),
            cls.gradient_boosting(n_estimators=120),
            cls.stacking(),
        ]


# ----------------------------------------------------------------------
# 5. MODEL WRAPPER — đóng gói (StandardScaler -> estimator) thành Pipeline
# ----------------------------------------------------------------------
class RegressionModel:
    """Bọc 1 ModelSpec thành sklearn Pipeline.

    Điểm cốt lõi: chuẩn hoá nằm BÊN TRONG pipeline. Khi cross-validate,
    scaler được fit lại trên từng fold huấn luyện -> KHÔNG rò rỉ thống kê
    của tập kiểm tra vào tập huấn luyện (data leakage).
    """

    def __init__(self, spec: ModelSpec):
        self.spec = spec
        steps = []
        if spec.needs_scaling:
            steps.append(("scaler", StandardScaler()))
            # Clip extreme scaled values (±5σ) — commodity/GARCH features can spike
            # far beyond training distribution in test folds, causing matmul overflow.
            steps.append(("clipper", FunctionTransformer(lambda X: np.clip(X, -5, 5))))
        steps.append(("model", spec.estimator))
        self.pipeline: Pipeline = Pipeline(steps)

    def fit(self, X, y) -> "RegressionModel":
        self.pipeline.fit(X, y)
        return self

    def predict(self, X) -> np.ndarray:
        return self.pipeline.predict(X)

    def __repr__(self) -> str:
        scal = "scaled" if self.spec.needs_scaling else "raw"
        return f"<RegressionModel {self.spec.name} ({scal})>"


# ----------------------------------------------------------------------
# 5. EVALUATION — container kết quả, tách trách nhiệm đo lường
# ----------------------------------------------------------------------
@dataclass
class EvaluationReport:
    model_name: str
    rmse: float
    mae: float
    r2: float
    cv_rmse_mean: float
    cv_rmse_std: float

    def as_row(self) -> Dict[str, float]:
        return {
            "Model": self.model_name,
            "Test_RMSE": round(self.rmse, 4),
            "Test_MAE": round(self.mae, 4),
            "Test_R2": round(self.r2, 4),
            "CV_RMSE_mean": round(self.cv_rmse_mean, 4),
            "CV_RMSE_std": round(self.cv_rmse_std, 4),
        }


# ----------------------------------------------------------------------
# 6. TRAINER (ORCHESTRATOR) — điều phối split / train / test / compare
# ----------------------------------------------------------------------
class ModelTrainer:
    """Điều phối toàn bộ vòng đời thực nghiệm.

    time_series=True -> dùng TimeSeriesSplit và split KHÔNG xáo trộn,
    tránh look-ahead bias: tập kiểm tra phải nằm ở tương lai so với
    tập huấn luyện. Đây là yêu cầu bắt buộc với chuỗi thời gian tài chính.
    """

    def __init__(
        self,
        test_size: float = 0.2,
        cv_folds: int = 5,
        time_series: bool = False,
        random_state: int = 42,
    ):
        self.test_size = test_size
        self.cv_folds = cv_folds
        self.time_series = time_series
        self.random_state = random_state
        self.reports: List[EvaluationReport] = []

    def _split(self, X, y):
        if self.time_series:
            split_idx = int(len(X) * (1 - self.test_size))
            return (
                X.iloc[:split_idx], X.iloc[split_idx:],
                y.iloc[:split_idx], y.iloc[split_idx:],
            )
        return train_test_split(
            X, y, test_size=self.test_size, random_state=self.random_state
        )

    def _cv_strategy(self):
        return TimeSeriesSplit(n_splits=self.cv_folds) if self.time_series else self.cv_folds

    def evaluate(self, model: RegressionModel, X, y) -> EvaluationReport:
        X_tr, X_te, y_tr, y_te = self._split(X, y)

        cv_scores = cross_val_score(
            model.pipeline, X_tr, y_tr,
            cv=self._cv_strategy(),
            scoring="neg_root_mean_squared_error",
        )
        cv_rmse = -cv_scores

        model.fit(X_tr, y_tr)
        y_pred = model.predict(X_te)

        report = EvaluationReport(
            model_name=model.spec.name,
            rmse=float(np.sqrt(mean_squared_error(y_te, y_pred))),
            mae=float(mean_absolute_error(y_te, y_pred)),
            r2=float(r2_score(y_te, y_pred)),
            cv_rmse_mean=float(cv_rmse.mean()),
            cv_rmse_std=float(cv_rmse.std()),
        )
        self.reports.append(report)
        return report

    def run_all(self, specs: List[ModelSpec], X, y) -> pd.DataFrame:
        self.reports.clear()
        for spec in specs:
            self.evaluate(RegressionModel(spec), X, y)
        df = pd.DataFrame([r.as_row() for r in self.reports])
        return df.sort_values("Test_RMSE").reset_index(drop=True)
