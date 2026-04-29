"""
CBOE Collector — VIX Daily History
====================================
What it fetches:
  • VIX daily OHLC (we use Close)                             → Grade A

Output schema:  list[MarketDataPoint]
  unit:      "index_level"
  frequency: "daily"

Limitations:
  - CSV URL may change if CBOE restructures their CDN
  - Only covers VIX (CBOE Volatility Index on S&P 500)
  - For other vol surfaces (VVIX, SKEW, 1-week VIX) check CBOE separately

Backup: Yahoo Finance (^VIX ticker) gives the same data with yfinance
"""
from __future__ import annotations

import logging
from datetime import date
from io import StringIO

from src.schema import MarketDataPoint
from .base_collector import BaseCollector

logger = logging.getLogger(__name__)

_VIX_CSV_URL = "https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv"


class CBOECollector(BaseCollector):
    """Fetches VIX daily history from CBOE's public CSV endpoint."""

    SOURCE_NAME:    str   = "CBOE"
    BASE_URL:       str   = "https://www.cboe.com"
    RATE_LIMIT_RPS: float = 0.2

    def fetch(self) -> list[MarketDataPoint]:
        try:
            resp = self.get(_VIX_CSV_URL)
            pts = self.parse_csv(resp.text, _VIX_CSV_URL)
            logger.info("CBOE VIX → %d points", len(pts))
            return pts
        except Exception as exc:
            logger.error("CBOE VIX fetch failed: %s", exc)
            return []

    @staticmethod
    def parse_csv(csv_text: str, source_url: str) -> list[MarketDataPoint]:
        """
        Parse CBOE VIX CSV into MarketDataPoint list.
        Expected columns: DATE, OPEN, HIGH, LOW, CLOSE
        Exposed as static so tests can call it without HTTP.
        """
        import pandas as pd

        try:
            df = pd.read_csv(StringIO(csv_text))
        except Exception as exc:
            logger.error("CBOE CSV parse error: %s", exc)
            return []

        # Normalise column names
        df.columns = [c.strip().upper() for c in df.columns]

        if "DATE" not in df.columns or "CLOSE" not in df.columns:
            logger.error("CBOE CSV unexpected columns: %s", list(df.columns))
            return []

        points: list[MarketDataPoint] = []
        for _, row in df.iterrows():
            date_str = str(row["DATE"]).strip()
            # CBOE uses M/D/YYYY format historically
            try:
                obs_date = pd.to_datetime(date_str).date()
            except Exception:
                continue

            raw: float | None = None
            try:
                raw = float(row["CLOSE"])
            except (ValueError, TypeError):
                pass

            points.append(
                MarketDataPoint(
                    as_of_date=obs_date,
                    field_name="VIX",
                    source_name="CBOE",
                    source_url=source_url,
                    raw_value=raw,
                    normalized_value=raw,
                    unit="index_level",
                    frequency="daily",
                    asset_class="equity",
                    region="US",
                    rating_bucket="na",
                    tenor_bucket="na",
                    rebuild_grade="A",
                    notes="CBOE Volatility Index (S&P 500 implied vol, 30-day)",
                )
            )
        return points
