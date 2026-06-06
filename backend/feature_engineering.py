"""
feature_engineering.py
----------------------
Kỹ thuật đặc trưng (feature engineering) cho dữ liệu giá cổ phiếu OHLCV.
Feature engineering là BẮT BUỘC: mô hình chỉ tốt bằng đặc trưng ta đưa vào.

NGUYÊN TẮC CHỐNG RÒ RỈ (no look-ahead):
  - Mọi đặc trưng tại thời điểm t chỉ dùng dữ liệu <= t.
  - Biến mục tiêu là lợi suất TƯƠNG LAI (t -> t+h), được shift NGƯỢC.
  - Sau khi tạo, dòng nào thiếu (do rolling/shift) bị loại -> không nội suy bừa.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


class FeatureBuilder:
    """Sinh đặc trưng kỹ thuật từ DataFrame OHLCV đã sắp xếp theo ngày tăng dần.

    Yêu cầu cột: ['date', 'open', 'high', 'low', 'close', 'volume'].
    """

    def __init__(self, horizon: int = 5):
        # horizon = số phiên dự báo về phía trước (5 ~ 1 tuần giao dịch)
        self.horizon = horizon

    @staticmethod
    def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(period).mean()
        loss = (-delta.clip(upper=0)).rolling(period).mean()
        rs = gain / loss.replace(0, np.nan)
        return 100 - (100 / (1 + rs))

    def build(self, df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
        d = df.sort_values("date").reset_index(drop=True).copy()
        c = d["close"]

        feat = pd.DataFrame(index=d.index)

        # --- Lợi suất trễ (momentum ngắn hạn) ---
        ret1 = c.pct_change()
        feat["ret_1d"] = ret1
        feat["ret_5d"] = c.pct_change(5)
        feat["ret_10d"] = c.pct_change(10)

        # --- Trung bình động & vị trí giá so với MA ---
        ma5, ma10, ma20 = c.rolling(5).mean(), c.rolling(10).mean(), c.rolling(20).mean()
        feat["price_to_ma20"] = c / ma20 - 1
        feat["ma5_to_ma20"] = ma5 / ma20 - 1          # tín hiệu cắt MA
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
        feat["volume_chg"] = d["volume"].pct_change()

        # --- Khoảng cách tới đỉnh/đáy 52 tuần (~252 phiên) ---
        roll_max = c.rolling(252, min_periods=20).max()
        roll_min = c.rolling(252, min_periods=20).min()
        feat["dist_52w_high"] = c / roll_max - 1
        feat["dist_52w_low"] = c / roll_min - 1

        # --- BIẾN MỤC TIÊU: lợi suất h phiên TƯƠNG LAI (shift ngược) ---
        target = c.shift(-self.horizon) / c - 1
        target.name = f"fwd_return_{self.horizon}d"

        # Loại NaN do rolling/shift; thay vô cực (chia 0) -> NaN rồi loại
        data = feat.replace([np.inf, -np.inf], np.nan)
        data = data.join(target)
        data = data.dropna().reset_index(drop=True)

        y = data[target.name]
        X = data.drop(columns=[target.name])
        return X, y
