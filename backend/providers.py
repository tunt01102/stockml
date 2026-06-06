"""
providers.py
------------
Lớp dữ liệu trừu tượng (Strategy + Factory). Cho phép MỌI mã chứng khoán,
không chỉ HPG. Tách nguồn dữ liệu khỏi phần phân tích.

  DataProvider        - interface chung
  VnstockProvider     - dữ liệu THẬT từ vnstock (chạy trên máy bạn)
  SyntheticProvider   - dữ liệu mô phỏng, seed theo mã -> mỗi mã 1 chuỗi ổn định
                        (dùng để demo/fallback khi không có mạng tới sàn)
"""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod

import numpy as np
import pandas as pd

OHLCV = ["date", "open", "high", "low", "close", "volume"]


class DataProvider(ABC):
    name: str = "base"

    @abstractmethod
    def fetch(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        """Trả DataFrame cột: date, open, high, low, close, volume (date tăng dần)."""
        raise NotImplementedError


class VnstockProvider(DataProvider):
    name = "vnstock"

    def fetch(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        from vnstock.api.quote import Quote  # vnstock >= 4.x API mới
        q = Quote(symbol=symbol.upper(), source="VCI")
        raw = q.history(start=start, end=end, interval="1D")
        raw = raw.rename(columns={"time": "date"})
        raw.columns = [c.lower() for c in raw.columns]
        df = raw[OHLCV].copy()
        df["date"] = pd.to_datetime(df["date"])
        return df.sort_values("date").reset_index(drop=True)


class SyntheticProvider(DataProvider):
    """Mô phỏng hiệu chỉnh theo chế độ thị trường VN 2020-2026.

    Seed dẫn xuất từ mã => mỗi mã có chuỗi khác nhau nhưng tái lập được.
    KHÔNG phải dữ liệu thật — chỉ để demo giao diện & kiểm thử pipeline.
    """
    name = "synthetic"

    def _seed(self, symbol: str) -> int:
        h = hashlib.sha256(symbol.upper().encode()).hexdigest()
        return int(h[:8], 16)

    def fetch(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        rng = np.random.default_rng(self._seed(symbol))
        dates = pd.bdate_range(start, end)
        n = len(dates)
        if n < 60:
            raise ValueError("Khoảng thời gian quá ngắn.")

        drift = np.zeros(n); vol = np.full(n, 0.020)
        yrs = dates.year
        drift[yrs <= 2021] = 0.0015; vol[yrs <= 2021] = 0.026
        drift[yrs == 2022] = -0.0017; vol[yrs == 2022] = 0.030
        drift[(yrs >= 2023) & (yrs <= 2024)] = 0.0009
        drift[yrs >= 2025] = 0.0003; vol[yrs >= 2025] = 0.018

        # biên độ riêng theo mã -> đa dạng hoá
        scale = 0.8 + (self._seed(symbol) % 100) / 250.0
        ret = rng.normal(drift * scale, vol * scale)
        for i in range(1, n):
            ret[i] += 0.04 * ret[i - 1]

        base = 5000 + self._seed(symbol) % 40000
        close = base * np.exp(np.cumsum(ret))
        high = close * (1 + np.abs(rng.normal(0, 0.012, n)))
        low = close * (1 - np.abs(rng.normal(0, 0.012, n)))
        open_ = low + (high - low) * rng.random(n)
        volume = rng.lognormal(17, 0.4, n).astype(int)

        return pd.DataFrame({"date": dates, "open": open_, "high": high,
                             "low": low, "close": close, "volume": volume})


def get_provider(prefer_real: bool = True) -> DataProvider:
    """Factory: ưu tiên vnstock nếu cài được, ngược lại synthetic."""
    if prefer_real:
        try:
            from vnstock.api.quote import Quote  # noqa: F401
            return VnstockProvider()
        except Exception:
            pass
    return SyntheticProvider()
