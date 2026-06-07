"""
data_cache.py
-------------
Disk cache cho dữ liệu OHLCV dùng Parquet, TTL 1 ngày.
Cache path: stockml/cache/{SYMBOL}_{start}_{end}.parquet
"""

from __future__ import annotations

import time
from pathlib import Path

import pandas as pd

CACHE_DIR = Path(__file__).parent.parent / "cache"
TTL_SECONDS = 86_400  # 1 ngày


def _cache_path(symbol: str, start: str, end: str) -> Path:
    return CACHE_DIR / f"{symbol.upper()}_{start}_{end}.parquet"


def load(symbol: str, start: str, end: str) -> pd.DataFrame | None:
    p = _cache_path(symbol, start, end)
    if p.exists() and (time.time() - p.stat().st_mtime) < TTL_SECONDS:
        return pd.read_parquet(p)
    return None


def save(symbol: str, start: str, end: str, df: pd.DataFrame) -> None:
    CACHE_DIR.mkdir(exist_ok=True)
    df.to_parquet(_cache_path(symbol, start, end))
