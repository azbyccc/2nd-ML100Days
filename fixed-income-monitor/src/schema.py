"""
Unified market data schema.

Every collector outputs List[MarketDataPoint]. This is the single contract
shared across collectors, storage, calculator, and output layers.

Grade coverage:
  A = directly reconstructable from public sources
  B = approximate; methodology may differ from Bloomberg
  C/D = excluded from this project
"""
from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, field_validator, model_validator

# ── Type aliases ──────────────────────────────────────────────────────────────

AssetClass   = Literal["rates", "credit", "equity", "fx", "commodity"]
Region       = Literal["US", "EU", "UK", "JP", "CA", "AU", "KR", "TW",
                        "ASIA", "LATAM", "EEMA", "EM", "GLOBAL"]
RatingBucket = Literal["na", "ig", "hy", "aaa", "aa", "a", "bbb", "bb", "b", "ccc"]
TenorBucket  = Literal["na", "overnight", "1w", "1m", "3m", "6m", "1y",
                        "2y", "3y", "5y", "7y", "10y", "20y", "30y"]
Frequency    = Literal["daily", "weekly", "monthly"]
Unit         = Literal["percent", "basis_points", "index_level", "fx_rate",
                        "usd_per_unit", "unknown"]
Grade        = Literal["A", "B", "C", "D"]


# ── Core data point ───────────────────────────────────────────────────────────

class MarketDataPoint(BaseModel):
    """
    One observation for one field on one date.

    raw_value        : value as received from the source (no conversion)
    normalized_value : after unit normalisation (e.g. FRED % → same %;
                       some FRED OAS series are already in bps)
    """

    # ── Identity ──────────────────────────────────────────────────────────────
    as_of_date:       date
    field_name:       str          # e.g. "US_TREASURY_10Y"
    source_name:      str          # e.g. "FRED"
    source_url:       str          # actual URL fetched

    # ── Values ────────────────────────────────────────────────────────────────
    raw_value:        Optional[float] = None
    normalized_value: Optional[float] = None   # None = missing / N/A
    unit:             Unit = "unknown"

    # ── Metadata ─────────────────────────────────────────────────────────────
    frequency:        Frequency    = "daily"
    asset_class:      AssetClass
    region:           Region
    rating_bucket:    RatingBucket = "na"
    tenor_bucket:     TenorBucket  = "na"
    rebuild_grade:    Grade        = "A"
    notes:            str          = ""

    # ── Validators ───────────────────────────────────────────────────────────

    @field_validator("field_name")
    @classmethod
    def field_name_uppercase(cls, v: str) -> str:
        return v.upper().strip()

    @model_validator(mode="after")
    def sync_normalized(self) -> "MarketDataPoint":
        # If normalized_value not explicitly set, copy raw_value
        if self.normalized_value is None and self.raw_value is not None:
            object.__setattr__(self, "normalized_value", self.raw_value)
        return self

    # ── Helpers ───────────────────────────────────────────────────────────────

    def is_missing(self) -> bool:
        return self.normalized_value is None

    def to_dict(self) -> dict:
        d = self.model_dump()
        d["as_of_date"] = d["as_of_date"].isoformat()
        return d


# ── Performance snapshot (output of calculator) ───────────────────────────────

class PerformanceSnapshot(BaseModel):
    """
    Adds D1 / WTD / MTD / YTD / 1W / 1M / 1Y change columns and
    a rolling 1-year percentile rank to a MarketDataPoint.

    Change semantics:
      rates / credit  → absolute change (same unit as normalized_value)
      equity / fx / commodity → percent return (%)
    """

    point:          MarketDataPoint
    d1:             Optional[float] = None   # vs prior business day
    wtd:            Optional[float] = None   # vs last Friday close
    mtd:            Optional[float] = None   # vs last month-end
    ytd:            Optional[float] = None   # vs prior year-end (Dec 31)
    chg_1w:         Optional[float] = None   # vs same weekday -7 cal days
    chg_1m:         Optional[float] = None   # vs ~1 month ago
    chg_1y:         Optional[float] = None   # vs ~1 year ago
    pct_rank_1y:    Optional[float] = None   # 0-100 percentile over last 252 bd

    def to_flat_dict(self) -> dict:
        """Flatten for DataFrame / CSV export."""
        base = self.point.to_dict()
        base.update({
            "d1":          self.d1,
            "wtd":         self.wtd,
            "mtd":         self.mtd,
            "ytd":         self.ytd,
            "chg_1w":      self.chg_1w,
            "chg_1m":      self.chg_1m,
            "chg_1y":      self.chg_1y,
            "pct_rank_1y": self.pct_rank_1y,
        })
        return base
