"""
Performance Calculator
======================
Computes D1 / WTD / MTD / YTD / 1W / 1M / 1Y changes and 1-year
percentile rank from stored historical data.

Design:
  - ALL changes are computed from the stored time-series — never from
    numbers pre-calculated by the data source.
  - Change semantics differ by asset class:
      rates / credit / fx → absolute change (same unit as value)
      equity / commodity  → percent return (%)
  - Reference dates:
      D1   = vs prior available business day
      WTD  = vs most recent Friday (or last available date before Mon)
      MTD  = vs last available day of prior month
      YTD  = vs Dec 31 of prior year (last available date)
      1W   = vs available date closest to -7 calendar days
      1M   = vs available date closest to -1 calendar month
      1Y   = vs available date closest to -12 calendar months

  - pct_rank_1y = percentile of today's value among all stored values
    in the past 252 business days (0 = lowest ever, 100 = highest ever)
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Optional

import numpy as np
import pandas as pd

from src.schema import MarketDataPoint, PerformanceSnapshot
from src.storage import HistoryStore

logger = logging.getLogger(__name__)

# Asset classes that use percent-return semantics
_PCT_RETURN_CLASSES = {"equity", "commodity"}


def _prior_biz_day(ref: date, dates_sorted: list[date]) -> Optional[date]:
    """Most recent date strictly before ref in dates_sorted."""
    candidates = [d for d in dates_sorted if d < ref]
    return candidates[-1] if candidates else None


def _closest_before(ref: date, dates_sorted: list[date]) -> Optional[date]:
    """Most recent date ≤ ref in dates_sorted."""
    candidates = [d for d in dates_sorted if d <= ref]
    return candidates[-1] if candidates else None


def _last_weekday(ref: date, weekday: int) -> date:
    """Most recent occurrence of `weekday` (Mon=0, Fri=4) on or before ref."""
    delta = (ref.weekday() - weekday) % 7
    return ref - timedelta(days=delta)


def _last_month_end(ref: date) -> date:
    first_of_month = ref.replace(day=1)
    return first_of_month - timedelta(days=1)


def _last_year_end(ref: date) -> date:
    return date(ref.year - 1, 12, 31)


def _n_months_back(ref: date, n: int) -> date:
    m = ref.month - n
    y = ref.year + m // 12
    m = m % 12
    if m == 0:
        m, y = 12, y - 1
    last_day = (date(y, m % 12 + 1, 1) - timedelta(days=1)).day if m < 12 else 31
    return date(y, m, min(ref.day, last_day))


class PerformanceCalculator:
    """
    Loads historical data from HistoryStore and computes a PerformanceSnapshot
    for each MarketDataPoint on the requested as_of_date.

    Usage:
        calc = PerformanceCalculator(store, as_of=date.today())
        snapshots = calc.compute(points)   # list[MarketDataPoint] for today
    """

    def __init__(self, store: HistoryStore, as_of: date | None = None):
        self.store = store
        self.as_of = as_of or date.today()

    def compute(self, points: list[MarketDataPoint]) -> list[PerformanceSnapshot]:
        """
        Compute performance for all points. Points must be for self.as_of date,
        but we look up history from the store for reference dates.
        """
        # Group today's points by field_name
        today_map: dict[str, MarketDataPoint] = {}
        for pt in points:
            if pt.as_of_date == self.as_of:
                today_map[pt.field_name] = pt
            # Also accept most-recent-available within ±1 day
            elif abs((pt.as_of_date - self.as_of).days) <= 1:
                today_map.setdefault(pt.field_name, pt)

        snapshots: list[PerformanceSnapshot] = []
        for field_name, today_pt in today_map.items():
            snap = self._compute_one(today_pt)
            snapshots.append(snap)

        logger.info("Performance computed for %d fields (as_of %s)", len(snapshots), self.as_of)
        return snapshots

    def compute_all_from_store(self) -> list[PerformanceSnapshot]:
        """
        Compute snapshots for all fields in the store using the most recent
        available data point. Useful for daily batch runs where today's data
        may not yet be available for all fields.
        """
        fields = self.store.available_fields()
        snapshots: list[PerformanceSnapshot] = []
        for field_name in fields:
            df = self.store.load(field_name, days=400)
            if df.empty or "normalized_value" not in df.columns:
                continue
            # Use most recent row as "today"
            latest_row = df.sort_values("as_of_date").iloc[-1]
            pt = self._row_to_point(latest_row, field_name)
            snap = self._compute_one(pt)
            snapshots.append(snap)
        return snapshots

    # ── Core computation ──────────────────────────────────────────────────────

    def _compute_one(self, today_pt: MarketDataPoint) -> PerformanceSnapshot:
        df = self.store.load(today_pt.field_name, days=400)
        if df.empty or "normalized_value" not in df.columns:
            logger.debug("No history for %s — returning snapshot without changes", today_pt.field_name)
            return PerformanceSnapshot(point=today_pt)

        df = df.sort_values("as_of_date").reset_index(drop=True)
        df["as_of_date"] = pd.to_datetime(df["as_of_date"]).dt.date
        df = df.dropna(subset=["normalized_value"])

        dates: list[date] = df["as_of_date"].tolist()
        value_map: dict[date, float] = dict(zip(df["as_of_date"], df["normalized_value"]))
        cur_val = today_pt.normalized_value

        use_pct = today_pt.asset_class in _PCT_RETURN_CLASSES

        def chg(ref_date: date | None) -> Optional[float]:
            if ref_date is None or cur_val is None:
                return None
            ref_actual = _closest_before(ref_date, dates)
            if ref_actual is None:
                return None
            ref_val = value_map.get(ref_actual)
            if ref_val is None:
                return None
            if use_pct:
                return round((cur_val / ref_val - 1) * 100, 4) if ref_val != 0 else None
            return round(cur_val - ref_val, 6)

        # Reference dates
        ref_d1  = _prior_biz_day(self.as_of, dates)
        ref_wtd = _last_weekday(self.as_of - timedelta(days=1) if self.as_of.weekday() == 0
                                else self.as_of, weekday=4)  # last Friday
        ref_mtd = _last_month_end(self.as_of)
        ref_ytd = _last_year_end(self.as_of)
        ref_1w  = self.as_of - timedelta(weeks=1)
        ref_1m  = _n_months_back(self.as_of, 1)
        ref_1y  = _n_months_back(self.as_of, 12)

        # 1-year percentile rank (last 252 available days)
        one_yr_ago = self.as_of - timedelta(days=365)
        hist_vals = df[df["as_of_date"] >= one_yr_ago]["normalized_value"].dropna()
        pct_rank: Optional[float] = None
        if len(hist_vals) >= 5 and cur_val is not None:
            pct_rank = round(float((hist_vals < cur_val).sum() / len(hist_vals) * 100), 1)

        return PerformanceSnapshot(
            point=today_pt,
            d1=chg(ref_d1),
            wtd=chg(ref_wtd),
            mtd=chg(ref_mtd),
            ytd=chg(ref_ytd),
            chg_1w=chg(ref_1w),
            chg_1m=chg(ref_1m),
            chg_1y=chg(ref_1y),
            pct_rank_1y=pct_rank,
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _row_to_point(row: pd.Series, field_name: str) -> MarketDataPoint:
        """Reconstruct a MarketDataPoint from a stored DataFrame row."""
        obs_date = row["as_of_date"]
        if not isinstance(obs_date, date):
            obs_date = pd.to_datetime(obs_date).date()

        # Pull metadata columns if stored; otherwise use safe defaults
        def _get(col: str, default: str) -> str:
            return str(row[col]) if col in row.index and pd.notna(row[col]) else default

        return MarketDataPoint(
            as_of_date=obs_date,
            field_name=field_name,
            source_name=_get("source_name", "UNKNOWN"),
            source_url=_get("source_url", ""),
            raw_value=row.get("raw_value"),
            normalized_value=row.get("normalized_value"),
            unit=_get("unit", "unknown"),                          # type: ignore[arg-type]
            frequency=_get("frequency", "daily"),                   # type: ignore[arg-type]
            asset_class=_get("asset_class", "rates"),               # type: ignore[arg-type]
            region=_get("region", "GLOBAL"),                        # type: ignore[arg-type]
            rating_bucket=_get("rating_bucket", "na"),              # type: ignore[arg-type]
            tenor_bucket=_get("tenor_bucket", "na"),                # type: ignore[arg-type]
            rebuild_grade=_get("rebuild_grade", "A"),               # type: ignore[arg-type]
            notes=_get("notes", ""),
        )
