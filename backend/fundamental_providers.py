"""
fundamental_providers.py
------------------------
Cung cấp yếu tố cơ bản:
  - P/E, P/B từ vnstock quarterly → resample to daily (forward-fill)
  - Giá nguyên liệu (iron ore TIO=F, steel HRC=F) từ yfinance (daily returns)

vnstock finance.ratio() trả DataFrame dạng transposed:
  - Rows = metrics (P/E, P/B, ROE, ...)
  - Columns = periods ('2018-Q1', '2019-Q2', ...)
  - item_id column có giá trị 'pe_ratio', 'pb_ratio' để lọc

Fallback an toàn: mọi lỗi đều log + trả None — không crash pipeline.
"""

from __future__ import annotations

import logging
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

_META_COLS = {"item", "item_en", "item_id", "period"}


class FundamentalProvider:

    def fetch_vnstock_ratios(
        self, symbol: str, start: str, end: str
    ) -> Optional[pd.DataFrame]:
        """P/E, P/B quarterly → reindex to business-day daily (forward-fill).

        vnstock finance.ratio() returns rows=metrics, cols=quarter-periods.
        """
        try:
            from vnstock.api.financial import Finance

            raw = Finance(symbol=symbol.upper(), source="VCI").ratio(period="quarter", lang="en")

            if raw is None or raw.empty:
                return None

            # Period columns are named like '2018-Q1', '2019-Q4', etc.
            period_cols = [c for c in raw.columns if c not in _META_COLS and "-Q" in str(c)]
            if not period_cols:
                logger.warning("vnstock ratios: no period columns found in %s", list(raw.columns))
                return None

            # item_id values may have whitespace — strip before comparing
            item_ids = raw["item_id"].astype(str).str.strip()
            pe_row = raw[item_ids == "pe_ratio"]
            pb_row = raw[item_ids == "pb_ratio"]

            if pe_row.empty and pb_row.empty:
                logger.warning("vnstock ratios: pe_ratio / pb_ratio rows not found")
                return None

            # Parse '2018-Q3' → end-of-quarter date
            def _col_to_date(col: str) -> Optional[pd.Timestamp]:
                try:
                    year_s, q_s = col.split("-Q")
                    year, quarter = int(year_s), int(q_s)
                    month = quarter * 3
                    return pd.Timestamp(year=year, month=month, day=1) + pd.offsets.MonthEnd(0)
                except Exception:
                    return None

            col_dates = {col: _col_to_date(col) for col in period_cols}
            valid_cols = [c for c, d in col_dates.items() if d is not None]

            if not valid_cols:
                return None

            result: dict = {}
            if not pe_row.empty:
                vals = pe_row.iloc[0][valid_cols].apply(pd.to_numeric, errors="coerce")
                result["pe_ratio"] = vals.values  # use .values so DataFrame index = date_idx
            if not pb_row.empty:
                vals = pb_row.iloc[0][valid_cols].apply(pd.to_numeric, errors="coerce")
                result["pb_ratio"] = vals.values

            date_idx = pd.DatetimeIndex([col_dates[c] for c in valid_cols])
            df = pd.DataFrame(result, index=date_idx)
            df = df[~df.index.duplicated(keep="last")].sort_index().dropna(how="all")

            # Reindex to business days in [start, end]
            bday_idx = pd.bdate_range(start=start, end=end)
            df = df.reindex(df.index.union(bday_idx)).sort_index().ffill().bfill()
            df = df.loc[bday_idx]
            df.index.name = "date"
            return df

        except Exception as exc:
            logger.warning("vnstock ratio fetch failed: %s", exc)
            return None

    def fetch_commodity(self, start: str, end: str) -> Optional[pd.DataFrame]:
        """Iron ore (TIO=F) + steel (HRC=F) daily % returns from yfinance.

        Returns DataFrame with DatetimeIndex and columns
        ['iron_ore_ret', 'steel_ret'], or None if unavailable.
        """
        try:
            import yfinance as yf

            tickers = ["TIO=F", "HRC=F"]
            raw = yf.download(
                tickers,
                start=start,
                end=end,
                auto_adjust=True,
                progress=False,
            )

            if raw is None or raw.empty:
                return None

            # yfinance MultiIndex columns when multiple tickers
            if isinstance(raw.columns, pd.MultiIndex):
                close = raw["Close"]
            elif "Close" in raw.columns:
                close = raw[["Close"]]
            else:
                close = raw

            if isinstance(close, pd.Series):
                close = close.to_frame()

            available = [t for t in tickers if t in close.columns]
            if not available:
                return None

            ret = close[available].pct_change(fill_method=None)
            rename = {"TIO=F": "iron_ore_ret", "HRC=F": "steel_ret"}
            ret = ret.rename(columns={t: rename[t] for t in available if t in rename})
            ret.index = pd.to_datetime(ret.index).normalize()
            ret.index.name = "date"
            return ret

        except Exception as exc:
            logger.warning("commodity price fetch failed: %s", exc)
            return None
