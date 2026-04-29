"""
ECB Collector — European Central Bank SDMX REST API
====================================================
What it fetches:
  • Euribor 1W / 1M / 3M / 6M / 12M                         → Grade A
  • ESTR (Euro Short-Term Rate, EONIA successor)              → Grade A
  • ECB AAA euro-area govt yield curve: 2Y / 5Y / 10Y / 30Y  → Grade A
  • ECB policy rates: DFR / MRO                               → Grade A

Output schema:  list[MarketDataPoint]
  unit:      "percent"
  frequency: "daily"

Limitations:
  - Yield curve covers AAA-rated euro-area sovereigns (Germany proxy),
    NOT single-country bonds (Italy, Spain, etc.)
  - ECB series keys change occasionally — if fetch fails, check:
    https://data-api.ecb.europa.eu/service/dataflow
  - Response is CSV when format=csvdata; parse accordingly
  - Not all series have full daily history; some gaps on ECB holidays

Backup: FRED has monthly German/French/Italian 10Y via OECD (coarser)
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from io import StringIO
from typing import Any

from src.schema import MarketDataPoint
from .base_collector import BaseCollector

logger = logging.getLogger(__name__)

_BASE = "https://data-api.ecb.europa.eu/service/data"

# ── Field registry ────────────────────────────────────────────────────────────
# (dataset, key, field_name, unit, rating_bucket, tenor_bucket, grade)

FIELDS: list[dict[str, Any]] = [
    # Euribor
    dict(ds="FM", key="B.U2.EUR.RT0.MM.EURIBOR1WD_.HSTA",  fn="EU_EURIBOR_1W",  unit="percent", rb="na", tb="1w",  gr="A"),
    dict(ds="FM", key="B.U2.EUR.RT0.MM.EURIBOR1MD_.HSTA",  fn="EU_EURIBOR_1M",  unit="percent", rb="na", tb="1m",  gr="A"),
    dict(ds="FM", key="B.U2.EUR.RT0.MM.EURIBOR3MD_.HSTA",  fn="EU_EURIBOR_3M",  unit="percent", rb="na", tb="3m",  gr="A"),
    dict(ds="FM", key="B.U2.EUR.RT0.MM.EURIBOR6MD_.HSTA",  fn="EU_EURIBOR_6M",  unit="percent", rb="na", tb="6m",  gr="A"),
    dict(ds="FM", key="B.U2.EUR.RT0.MM.EURIBOR1YD_.HSTA",  fn="EU_EURIBOR_12M", unit="percent", rb="na", tb="1y",  gr="A"),
    # ESTR
    dict(ds="EST", key="B.EU000A2X2A25.WT",                fn="EU_ESTR",        unit="percent", rb="na", tb="overnight", gr="A"),
    # ECB policy rates
    dict(ds="FM", key="B.U2.EUR.4F.KR.DFR.LEV",            fn="EU_ECB_DFR",     unit="percent", rb="na", tb="overnight", gr="A"),
    dict(ds="FM", key="B.U2.EUR.4F.KR.MRR_FR.LEV",         fn="EU_ECB_MRO",     unit="percent", rb="na", tb="overnight", gr="A"),
    # ECB AAA yield curve (Svensson model — euro-area AAA-rated govts)
    dict(ds="YC", key="B.U2.EUR.4F.G_N_A.SV_C_YM.SR_2Y",  fn="EU_AAA_YIELD_2Y",  unit="percent", rb="aaa", tb="2y",  gr="A",
         notes="ECB AAA euro-area govt yield curve (proxy for Germany)"),
    dict(ds="YC", key="B.U2.EUR.4F.G_N_A.SV_C_YM.SR_5Y",  fn="EU_AAA_YIELD_5Y",  unit="percent", rb="aaa", tb="5y",  gr="A"),
    dict(ds="YC", key="B.U2.EUR.4F.G_N_A.SV_C_YM.SR_10Y", fn="EU_AAA_YIELD_10Y", unit="percent", rb="aaa", tb="10y", gr="A"),
    dict(ds="YC", key="B.U2.EUR.4F.G_N_A.SV_C_YM.SR_30Y", fn="EU_AAA_YIELD_30Y", unit="percent", rb="aaa", tb="30y", gr="A"),
]

_LOOKBACK_DAYS = 400


class ECBCollector(BaseCollector):
    """Fetches euro-area money market rates and yield curve from ECB SDMX API."""

    SOURCE_NAME:    str   = "ECB"
    BASE_URL:       str   = "https://data-api.ecb.europa.eu"
    RATE_LIMIT_RPS: float = 0.5

    def fetch(self) -> list[MarketDataPoint]:
        start = (date.today() - timedelta(days=_LOOKBACK_DAYS)).strftime("%Y-%m-%d")
        results: list[MarketDataPoint] = []

        for field in FIELDS:
            try:
                pts = self._fetch_series(field, start)
                results.extend(pts)
                logger.info("ECB %-25s → %3d points", field["fn"], len(pts))
            except Exception as exc:
                logger.error("ECB %s failed: %s", field["fn"], exc)

        return results

    def _fetch_series(self, field: dict, start: str) -> list[MarketDataPoint]:
        url = f"{_BASE}/{field['ds']}/{field['key']}"
        params = {"format": "csvdata", "startPeriod": start, "detail": "dataonly"}
        resp = self.get(url, params=params)
        return self.parse_csv(resp.text, field, url)

    @staticmethod
    def parse_csv(csv_text: str, field: dict, source_url: str) -> list[MarketDataPoint]:
        """
        Parse ECB CSV response into MarketDataPoint list.
        Exposed as static so tests can call it without HTTP.
        """
        lines = csv_text.strip().splitlines()
        if len(lines) < 2:
            return []

        headers = [h.strip().strip('"') for h in lines[0].split(",")]

        # Find TIME_PERIOD and OBS_VALUE columns
        period_idx = next((i for i, h in enumerate(headers) if "TIME_PERIOD" in h.upper()), None)
        value_idx  = next((i for i, h in enumerate(headers) if "OBS_VALUE"   in h.upper()), None)

        if period_idx is None or value_idx is None:
            logger.warning("ECB CSV: missing TIME_PERIOD or OBS_VALUE in headers: %s", headers[:5])
            return []

        points: list[MarketDataPoint] = []
        for line in lines[1:]:
            if not line.strip():
                continue
            parts = line.split(",")
            if len(parts) <= max(period_idx, value_idx):
                continue
            period_str = parts[period_idx].strip().strip('"')
            val_str    = parts[value_idx].strip().strip('"')

            # ECB dates can be YYYY-MM-DD or YYYY-MM (monthly) — normalise
            try:
                if len(period_str) == 7:   # YYYY-MM → use last day of month
                    import calendar
                    y, m = int(period_str[:4]), int(period_str[5:7])
                    obs_date = date(y, m, calendar.monthrange(y, m)[1])
                else:
                    obs_date = date.fromisoformat(period_str[:10])
            except ValueError:
                continue

            raw: float | None = None
            try:
                raw = float(val_str) if val_str else None
            except ValueError:
                pass

            points.append(
                MarketDataPoint(
                    as_of_date=obs_date,
                    field_name=field["fn"],
                    source_name="ECB",
                    source_url=source_url,
                    raw_value=raw,
                    normalized_value=raw,
                    unit="percent",
                    frequency="daily",
                    asset_class="rates",
                    region="EU",
                    rating_bucket=field.get("rb", "na"),   # type: ignore[arg-type]
                    tenor_bucket=field.get("tb", "na"),    # type: ignore[arg-type]
                    rebuild_grade=field.get("gr", "A"),    # type: ignore[arg-type]
                    notes=field.get("notes", ""),
                )
            )
        return points
