"""
Historical data storage layer.

Strategy: one Parquet file per field_name, stored under data/history/.
  data/history/US_TREASURY_10Y.parquet
  data/history/US_HY_OAS.parquet
  ...

Each file is a time-series with columns matching MarketDataPoint.to_dict().
New observations are appended with deduplication on (field_name, as_of_date).

If pyarrow is unavailable, falls back to CSV automatically.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

# Check backend availability once at import time
try:
    import pyarrow  # noqa: F401
    _USE_PARQUET = True
except ImportError:
    _USE_PARQUET = False
    logger.warning("pyarrow not installed — using CSV fallback. pip install pyarrow")

_EXT = ".parquet" if _USE_PARQUET else ".csv"


def _read(path: Path) -> pd.DataFrame:
    if path.suffix == ".parquet":
        return pd.read_parquet(path)
    return pd.read_csv(path, parse_dates=["as_of_date"])


def _write(df: pd.DataFrame, path: Path) -> None:
    if path.suffix == ".parquet":
        df.to_parquet(path, index=False, compression="snappy")
    else:
        df.to_csv(path, index=False)


class HistoryStore:
    """
    Append-only store for daily market data points.

    Usage:
        store = HistoryStore("data/history")
        store.append(points)                         # save new data
        df = store.load("US_TREASURY_10Y", days=400) # load history
    """

    DATE_COL = "as_of_date"

    def __init__(self, history_dir: str = "data/history"):
        self.root = Path(history_dir)
        self.root.mkdir(parents=True, exist_ok=True)

    # ── Write ─────────────────────────────────────────────────────────────────

    def append(self, points: list[dict]) -> dict[str, int]:
        """
        Append a list of MarketDataPoint.to_dict() records.
        Deduplicates on (field_name, as_of_date) — latest record wins.
        Returns {field_name: rows_added} summary.
        """
        if not points:
            return {}

        df_new = pd.DataFrame(points)
        df_new[self.DATE_COL] = pd.to_datetime(df_new[self.DATE_COL]).dt.date

        summary: dict[str, int] = {}

        for field_name, grp in df_new.groupby("field_name"):
            path = self.root / f"{field_name}{_EXT}"

            if path.exists():
                df_old = _read(path)
                df_old[self.DATE_COL] = pd.to_datetime(df_old[self.DATE_COL]).dt.date
                df_merged = pd.concat([df_old, grp], ignore_index=True)
            else:
                df_merged = grp.copy()

            # Deduplicate: last write wins
            before = len(df_merged)
            df_merged = (
                df_merged
                .sort_values(self.DATE_COL)
                .drop_duplicates(subset=[self.DATE_COL], keep="last")
                .reset_index(drop=True)
            )
            added = len(df_merged) - (before - len(grp))
            _write(df_merged, path)
            summary[field_name] = max(added, 0)
            logger.debug("Stored %s → %s (+%d rows)", field_name, path.name, added)

        return summary

    # ── Read ──────────────────────────────────────────────────────────────────

    def load(self, field_name: str, days: int = 400) -> pd.DataFrame:
        """
        Load history for a single field.
        Returns DataFrame sorted by as_of_date ascending, last `days` calendar days.
        Returns empty DataFrame if field not found.
        """
        path = self.root / f"{field_name}{_EXT}"
        if not path.exists():
            logger.debug("No history for %s", field_name)
            return pd.DataFrame()

        df = _read(path)
        df[self.DATE_COL] = pd.to_datetime(df[self.DATE_COL]).dt.date
        cutoff = date.today() - timedelta(days=days)
        df = df[df[self.DATE_COL] >= cutoff].sort_values(self.DATE_COL).reset_index(drop=True)
        return df

    def load_many(self, field_names: list[str], days: int = 400) -> pd.DataFrame:
        """Load and concatenate history for multiple fields."""
        frames = [self.load(f, days=days) for f in field_names]
        frames = [f for f in frames if not f.empty]
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    def available_fields(self) -> list[str]:
        """Return list of field names that have stored history."""
        return [
            p.stem for p in self.root.iterdir()
            if p.suffix in (".parquet", ".csv") and not p.name.startswith(".")
        ]

    def latest_date(self, field_name: str) -> Optional[date]:
        """Return the most recent stored date for a field."""
        df = self.load(field_name, days=10)
        if df.empty:
            return None
        return df[self.DATE_COL].max()

    # ── Maintenance ───────────────────────────────────────────────────────────

    def prune(self, keep_days: int = 400) -> None:
        """Remove observations older than keep_days from all field files."""
        cutoff = date.today() - timedelta(days=keep_days)
        for path in self.root.glob(f"*{_EXT}"):
            df = _read(path)
            df[self.DATE_COL] = pd.to_datetime(df[self.DATE_COL]).dt.date
            df_pruned = df[df[self.DATE_COL] >= cutoff].reset_index(drop=True)
            if len(df_pruned) < len(df):
                _write(df_pruned, path)
                logger.info("Pruned %s: removed %d old rows", path.name, len(df) - len(df_pruned))
