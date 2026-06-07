"""
feature_engineering.py
----------------------
Kỹ thuật đặc trưng (feature engineering) cho dữ liệu giá cổ phiếu OHLCV.
Feature engineering là BẮT BUỘC: mô hình chỉ tốt bằng đặc trưng ta đưa vào.

NGUYÊN TẮC CHỐNG RÒ RỈ (no look-ahead):
  - Mọi đặc trưng tại thời điểm t chỉ dùng dữ liệu <= t.
  - Biến mục tiêu là lợi suất / biến động TƯƠNG LAI (t -> t+h), được shift NGƯỢC.
  - Sau khi tạo, dòng nào thiếu (do rolling/shift) bị loại -> không nội suy bừa.

mode="return"     : mục tiêu = lợi suất h phiên tới (fwd_return_Nd)
mode="volatility" : mục tiêu = độ lệch chuẩn lợi suất h phiên tới (fwd_vol_Nd)
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def _add_garch_features(d: pd.DataFrame, feat: pd.DataFrame) -> pd.DataFrame:
    """Thêm 2 cột GARCH(1,1): conditional variance tại t và 1-step forecast.

    Dùng arch library. Fallback im lặng nếu không cài hoặc fit thất bại.
    """
    try:
        from arch import arch_model

        ret_pct = d["close"].pct_change(fill_method=None).dropna() * 100
        if len(ret_pct) < 50:
            return feat

        am = arch_model(ret_pct, vol="Garch", p=1, q=1, dist="normal")
        res = am.fit(disp="off", show_warning=False)

        cond_var = (res.conditional_volatility ** 2).reindex(d.index)
        # start=0 → trả về 1-step forecast cho TỪNG quan sát (không chỉ terminal)
        forecast_var = res.forecast(horizon=1, start=0).variance.iloc[:, 0].reindex(d.index)

        feat = feat.copy()
        feat["garch_var_t"] = cond_var.values
        feat["garch_forecast_t"] = forecast_var.values
    except Exception as exc:
        logger.warning("GARCH features skipped: %s", exc)

    return feat


def _join_fundamental(
    d: pd.DataFrame,
    feat: pd.DataFrame,
    fundamental_df: pd.DataFrame,
) -> pd.DataFrame:
    """Join fundamental features (PE, PB, commodity returns) bằng ngày giao dịch."""
    dates = pd.DatetimeIndex(d["date"].dt.normalize())
    try:
        aligned = fundamental_df.reindex(dates)
        feat = feat.copy()
        for col in aligned.columns:
            feat[col] = aligned[col].values
    except Exception as exc:
        logger.warning("fundamental join skipped: %s", exc)
    return feat


class FeatureBuilder:
    """Sinh đặc trưng kỹ thuật từ DataFrame OHLCV đã sắp xếp theo ngày tăng dần.

    Yêu cầu cột: ['date', 'open', 'high', 'low', 'close', 'volume'].

    mode="return"     → target = lợi suất h phiên tới
    mode="volatility" → target = realized vol h phiên tới (rolling std of returns)
    """

    def __init__(self, horizon: int = 5, mode: str = "return"):
        self.horizon = horizon
        self.mode = mode

    @staticmethod
    def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(period).mean()
        loss = (-delta.clip(upper=0)).rolling(period).mean()
        rs = gain / loss.replace(0, np.nan)
        return 100 - (100 / (1 + rs))

    def build(
        self,
        df: pd.DataFrame,
        fundamental_df: Optional[pd.DataFrame] = None,
    ) -> tuple[pd.DataFrame, pd.Series]:
        d = df.sort_values("date").reset_index(drop=True).copy()
        c = d["close"]

        feat = pd.DataFrame(index=d.index)

        # --- Lợi suất trễ (momentum ngắn hạn) ---
        ret1 = c.pct_change(fill_method=None)
        feat["ret_1d"] = ret1
        feat["ret_5d"] = c.pct_change(5, fill_method=None)
        feat["ret_10d"] = c.pct_change(10, fill_method=None)

        # --- Trung bình động & vị trí giá so với MA ---
        ma5, ma10, ma20 = c.rolling(5).mean(), c.rolling(10).mean(), c.rolling(20).mean()
        feat["price_to_ma20"] = c / ma20 - 1
        feat["ma5_to_ma20"] = ma5 / ma20 - 1
        feat["ma10_to_ma20"] = ma10 / ma20 - 1

        # --- Biến động (rolling volatility) ---
        feat["vol_10d"] = ret1.rolling(10).std()
        feat["vol_20d"] = ret1.rolling(20).std()

        # --- RSI: quá mua / quá bán ---
        feat["rsi_14"] = self._rsi(c, 14) / 100.0

        # --- Biên độ trong phiên & vị trí đóng cửa ---
        feat["hl_range"] = (d["high"] - d["low"]) / c
        feat["close_pos"] = (c - d["low"]) / (d["high"] - d["low"]).replace(0, np.nan)

        # --- Đặc trưng khối lượng ---
        vma20 = d["volume"].rolling(20).mean()
        feat["vol_ratio"] = d["volume"] / vma20
        feat["volume_chg"] = d["volume"].pct_change(fill_method=None)

        # --- Khoảng cách tới đỉnh/đáy 52 tuần (~252 phiên) ---
        roll_max = c.rolling(252, min_periods=20).max()
        roll_min = c.rolling(252, min_periods=20).min()
        feat["dist_52w_high"] = c / roll_max - 1
        feat["dist_52w_low"] = c / roll_min - 1

        # --- GARCH(1,1): conditional variance + 1-step forecast ---
        feat = _add_garch_features(d, feat)

        # --- Yếu tố cơ bản (nếu có) ---
        if fundamental_df is not None and not fundamental_df.empty:
            feat = _join_fundamental(d, feat, fundamental_df)

        # --- BIẾN MỤC TIÊU ---
        if self.mode == "volatility":
            # Realized volatility: rolling std của lợi suất h phiên tới
            target = ret1.rolling(self.horizon).std().shift(-self.horizon)
            target.name = f"fwd_vol_{self.horizon}d"
        else:
            # Lợi suất h phiên tương lai
            target = c.shift(-self.horizon) / c - 1
            target.name = f"fwd_return_{self.horizon}d"

        # Loại NaN do rolling/shift; thay vô cực (chia 0) -> NaN rồi loại
        data = feat.replace([np.inf, -np.inf], np.nan)
        data = data.join(target)
        data = data.dropna().reset_index(drop=True)

        y = data[target.name]
        X = data.drop(columns=[target.name])
        return X, y
