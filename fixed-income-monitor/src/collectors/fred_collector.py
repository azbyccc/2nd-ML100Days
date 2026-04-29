"""
FRED Collector — Federal Reserve Economic Data (St. Louis Fed)
==============================================================
What it fetches:
  • US Treasury nominal yields  (2Y / 5Y / 10Y / 30Y)     → Grade A
  • TIPS real yields            (5Y / 10Y)                  → Grade A
  • Breakeven inflation rates   (5Y / 10Y)                  → Grade A
  • ICE BofA credit OAS        (IG / HY / BB / B / CCC)   → Grade A
  • ICE BofA effective yields   (IG / HY)                   → Grade A
  • Fallen Angel OAS                                         → Grade A
  • SOFR / Effective Fed Funds Rate                          → Grade A

Output schema:  list[MarketDataPoint]
  unit:  "percent" for yields/rates; "basis_points" for OAS spreads
  frequency: daily (business days only — weekends/holidays are NaN in FRED)

Limitations:
  - Requires free FRED_API_KEY env var (register at fred.stlouisfed.org)
  - FRED OAS series lag Bloomberg by ~1 business day (T+1 publish)
  - DM sovereign yields via FRED are monthly (OECD source) — use
    Treasury.gov or ECB collectors for daily DM yields
  - JPM EMBI / CEMBI not available → Grade D, excluded
"""
from __future__ import annotations

import logging
import os
from datetime import date, timedelta
from typing import Any

from src.schema import MarketDataPoint
from .base_collector import BaseCollector

logger = logging.getLogger(__name__)

FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"

# ── Field registry ────────────────────────────────────────────────────────────
# Each entry: (fred_series_id, field_name, unit, asset_class, region,
#              rating_bucket, tenor_bucket, rebuild_grade)

FIELDS: list[dict[str, Any]] = [
    # US Treasuries
    dict(sid="DGS2",   fn="US_TREASURY_2Y",  unit="percent",      ac="rates",    rg="US",  rb="na",  tb="2y",  gr="A"),
    dict(sid="DGS5",   fn="US_TREASURY_5Y",  unit="percent",      ac="rates",    rg="US",  rb="na",  tb="5y",  gr="A"),
    dict(sid="DGS10",  fn="US_TREASURY_10Y", unit="percent",      ac="rates",    rg="US",  rb="na",  tb="10y", gr="A"),
    dict(sid="DGS30",  fn="US_TREASURY_30Y", unit="percent",      ac="rates",    rg="US",  rb="na",  tb="30y", gr="A"),
    # TIPS real yields
    dict(sid="DFII5",  fn="US_TIPS_5Y",      unit="percent",      ac="rates",    rg="US",  rb="na",  tb="5y",  gr="A"),
    dict(sid="DFII10", fn="US_TIPS_10Y",     unit="percent",      ac="rates",    rg="US",  rb="na",  tb="10y", gr="A"),
    # Breakeven inflation
    dict(sid="T5YIE",  fn="US_BEI_5Y",       unit="percent",      ac="rates",    rg="US",  rb="na",  tb="5y",  gr="A"),
    dict(sid="T10YIE", fn="US_BEI_10Y",      unit="percent",      ac="rates",    rg="US",  rb="na",  tb="10y", gr="A"),
    # Yield curve spread
    dict(sid="T10Y2Y", fn="US_CURVE_10Y2Y",  unit="percent",      ac="rates",    rg="US",  rb="na",  tb="na",  gr="A"),
    # Money market
    dict(sid="SOFR",   fn="US_SOFR",         unit="percent",      ac="rates",    rg="US",  rb="na",  tb="overnight", gr="A"),
    dict(sid="EFFR",   fn="US_EFFR",         unit="percent",      ac="rates",    rg="US",  rb="na",  tb="overnight", gr="A"),
    # ICE BofA OAS (basis points)
    dict(sid="BAMLC0A0CM",    fn="US_IG_OAS",    unit="basis_points", ac="credit", rg="US", rb="ig",  tb="na", gr="A"),
    dict(sid="BAMLH0A0HYM2",  fn="US_HY_OAS",    unit="basis_points", ac="credit", rg="US", rb="hy",  tb="na", gr="A"),
    dict(sid="BAMLC0A4CBBB",  fn="US_BBB_OAS",   unit="basis_points", ac="credit", rg="US", rb="bbb", tb="na", gr="A"),
    dict(sid="BAMLH0A1HYBB",  fn="US_BB_OAS",    unit="basis_points", ac="credit", rg="US", rb="bb",  tb="na", gr="A"),
    dict(sid="BAMLH0A2HYB",   fn="US_B_OAS",     unit="basis_points", ac="credit", rg="US", rb="b",   tb="na", gr="A"),
    dict(sid="BAMLH0A3HYC",   fn="US_CCC_OAS",   unit="basis_points", ac="credit", rg="US", rb="ccc", tb="na", gr="A"),
    dict(sid="BAMLH0A4FANDOAS",fn="US_FA_OAS",   unit="basis_points", ac="credit", rg="US", rb="hy",  tb="na", gr="A",
         notes="Fallen Angel OAS"),
    # ICE BofA Effective Yields (percent)
    dict(sid="BAMLC0A0CMEY",   fn="US_IG_YIELD",  unit="percent",      ac="credit", rg="US", rb="ig",  tb="na", gr="A"),
    dict(sid="BAMLH0A0HYM2EY", fn="US_HY_YIELD",  unit="percent",      ac="credit", rg="US", rb="hy",  tb="na", gr="A"),
    dict(sid="BAMLH0A1HYBBEY", fn="US_BB_YIELD",  unit="percent",      ac="credit", rg="US", rb="bb",  tb="na", gr="A"),
    dict(sid="BAMLH0A2HYBEY",  fn="US_B_YIELD",   unit="percent",      ac="credit", rg="US", rb="b",   tb="na", gr="A"),
    dict(sid="BAMLH0A3HYCEY",  fn="US_CCC_YIELD", unit="percent",      ac="credit", rg="US", rb="ccc", tb="na", gr="A"),
    # ICE BofA Euro HY
    dict(sid="BAMLHE00EHYIOAS", fn="EU_HY_OAS",   unit="basis_points", ac="credit", rg="EU", rb="hy",  tb="na", gr="A"),
    dict(sid="BAMLHE00EHYIEY",  fn="EU_HY_YIELD", unit="percent",      ac="credit", rg="EU", rb="hy",  tb="na", gr="A"),
    # ICE BofA EM
    dict(sid="BAMLEMHBHYCROAS",  fn="EM_HY_OAS",   unit="basis_points", ac="credit", rg="EM", rb="hy", tb="na", gr="B",
         notes="ICE BofA EM HY Corp; methodology differs from JPM CEMBI"),
    dict(sid="BAMLEMIBHGCROAS",  fn="EM_IG_OAS",   unit="basis_points", ac="credit", rg="EM", rb="ig", tb="na", gr="B",
         notes="ICE BofA EM IG Corp; methodology differs from JPM CEMBI"),
    dict(sid="BAMLEMHBHYCRPIEY", fn="EM_HY_YIELD", unit="percent",      ac="credit", rg="EM", rb="hy", tb="na", gr="B"),
    dict(sid="BAMLEMIBHGCRPIEY", fn="EM_IG_YIELD", unit="percent",      ac="credit", rg="EM", rb="ig", tb="na", gr="B"),
]

_LOOKBACK_DAYS = 400


class FREDCollector(BaseCollector):
    """
    Fetches FRED time-series via the official JSON API.
    API key: free at https://fred.stlouisfed.org/docs/api/api_key.html
    Set env var FRED_API_KEY before running.
    """

    SOURCE_NAME:    str   = "FRED"
    BASE_URL:       str   = "https://api.stlouisfed.org"
    RATE_LIMIT_RPS: float = 0.5   # conservative for free tier

    def __init__(self, api_key: str | None = None) -> None:
        super().__init__()
        self.api_key = api_key or os.getenv("FRED_API_KEY", "")
        if not self.api_key:
            logger.warning(
                "FRED_API_KEY not set — FRED collector will return no data. "
                "Get a free key at https://fred.stlouisfed.org/docs/api/api_key.html"
            )

    def fetch(self) -> list[MarketDataPoint]:
        if not self.api_key:
            return []

        start = (date.today() - timedelta(days=_LOOKBACK_DAYS)).isoformat()
        results: list[MarketDataPoint] = []

        for field in FIELDS:
            try:
                pts = self._fetch_series(field, start)
                results.extend(pts)
                logger.info("FRED %-25s → %3d points", field["fn"], len(pts))
            except Exception as exc:
                logger.error("FRED %s (%s) failed: %s", field["fn"], field["sid"], exc)

        return results

    # ── Parsing helpers ───────────────────────────────────────────────────────

    def _fetch_series(self, field: dict, start: str) -> list[MarketDataPoint]:
        url = FRED_BASE
        params = {
            "series_id":          field["sid"],
            "api_key":            self.api_key,
            "file_type":          "json",
            "observation_start":  start,
            "sort_order":         "asc",
        }
        resp = self.get(url, params=params)
        return self.parse_observations(resp.json().get("observations", []), field, url)

    @staticmethod
    def parse_observations(
        observations: list[dict],
        field: dict,
        source_url: str,
    ) -> list[MarketDataPoint]:
        """
        Parse FRED observation list into MarketDataPoint list.
        Exposed as static method so tests can call it without HTTP.
        """
        points: list[MarketDataPoint] = []
        for obs in observations:
            val_str = obs.get("value", ".")
            raw = None if val_str == "." else float(val_str)
            points.append(
                MarketDataPoint(
                    as_of_date=date.fromisoformat(obs["date"]),
                    field_name=field["fn"],
                    source_name="FRED",
                    source_url=source_url,
                    raw_value=raw,
                    normalized_value=raw,
                    unit=field["unit"],           # type: ignore[arg-type]
                    frequency="daily",
                    asset_class=field["ac"],      # type: ignore[arg-type]
                    region=field["rg"],            # type: ignore[arg-type]
                    rating_bucket=field.get("rb", "na"),   # type: ignore[arg-type]
                    tenor_bucket=field.get("tb", "na"),    # type: ignore[arg-type]
                    rebuild_grade=field.get("gr", "A"),    # type: ignore[arg-type]
                    notes=field.get("notes", ""),
                )
            )
        return points
