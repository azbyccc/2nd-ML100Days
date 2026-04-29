"""
Treasury.gov Collector — Official US Daily Yield Curve
=======================================================
What it fetches:
  • US Treasury nominal par yield curve (1M / 3M / 6M / 1Y / 2Y / 3Y /
    5Y / 7Y / 10Y / 20Y / 30Y)                               → Grade A

Output schema:  list[MarketDataPoint]
  unit:      "percent"
  frequency: "daily"

Limitations:
  - XML feed is published next business day (~18:00 ET)
  - No TIPS or BEI data (use FRED collector for those)
  - Only covers US Treasuries; all non-US rates are excluded
  - URL pattern may change when Treasury redesigns the site; check if
    fetch fails after a site migration

Backup: FRED DGS series (same underlying data, slight delay)
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any
from xml.etree import ElementTree as ET

from src.schema import MarketDataPoint
from .base_collector import BaseCollector

logger = logging.getLogger(__name__)

_BASE = "https://home.treasury.gov"
_URL_TMPL = (
    "{base}/resource-center/data-chart-center/interest-rates/pages/"
    "xml-data-download?data=daily_treasury_yield_curve"
    "&field_tdr_date_value={year}{month:02d}"
)

# XML namespace used by Treasury's Atom feed
_NS_ATOM  = "http://www.w3.org/2005/Atom"
_NS_DS    = "http://schemas.microsoft.com/ado/2007/08/dataservices"
_NS_META  = "http://schemas.microsoft.com/ado/2007/08/dataservices/metadata"

# Map XML tag → (field_name, tenor_bucket)
_TENOR_MAP: dict[str, tuple[str, str]] = {
    "BC_1MONTH":  ("US_TREASURY_1M",  "1m"),
    "BC_3MONTH":  ("US_TREASURY_3M",  "3m"),
    "BC_6MONTH":  ("US_TREASURY_6M",  "6m"),
    "BC_1YEAR":   ("US_TREASURY_1Y",  "1y"),
    "BC_2YEAR":   ("US_TREASURY_2Y",  "2y"),
    "BC_3YEAR":   ("US_TREASURY_3Y",  "3y"),
    "BC_5YEAR":   ("US_TREASURY_5Y",  "5y"),
    "BC_7YEAR":   ("US_TREASURY_7Y",  "7y"),
    "BC_10YEAR":  ("US_TREASURY_10Y", "10y"),
    "BC_20YEAR":  ("US_TREASURY_20Y", "20y"),
    "BC_30YEAR":  ("US_TREASURY_30Y", "30y"),
}


class TreasuryGovCollector(BaseCollector):
    """
    Parses the official Treasury yield curve Atom/XML feed.
    Fetches current month + prior month to handle month-start gaps.
    """

    SOURCE_NAME:    str   = "TREASURY_GOV"
    BASE_URL:       str   = _BASE
    RATE_LIMIT_RPS: float = 0.2   # be conservative on government servers

    def fetch(self) -> list[MarketDataPoint]:
        today = date.today()
        months: list[tuple[int, int]] = [(today.year, today.month)]
        # Also grab prior month (last ~5 biz days may not yet be in current month)
        prior = today.replace(day=1) - timedelta(days=1)
        months.append((prior.year, prior.month))

        results: list[MarketDataPoint] = []
        for year, month in months:
            url = _URL_TMPL.format(base=_BASE, year=year, month=month)
            try:
                resp = self.get(url)
                pts = self.parse_xml(resp.text, url)
                results.extend(pts)
                logger.info("Treasury.gov %d-%02d → %d observations", year, month, len(pts))
            except Exception as exc:
                logger.error("Treasury.gov %d-%02d failed: %s", year, month, exc)

        # Deduplicate (same date may appear in both months' feeds)
        seen: set[tuple[str, date]] = set()
        deduped: list[MarketDataPoint] = []
        for pt in results:
            key = (pt.field_name, pt.as_of_date)
            if key not in seen:
                seen.add(key)
                deduped.append(pt)
        return deduped

    @staticmethod
    def parse_xml(xml_text: str, source_url: str) -> list[MarketDataPoint]:
        """
        Parse Treasury Atom XML into MarketDataPoint list.
        Exposed as static so tests can call it without HTTP.
        """
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as exc:
            logger.error("Treasury XML parse error: %s", exc)
            return []

        points: list[MarketDataPoint] = []

        for entry in root.findall(f"{{{_NS_ATOM}}}entry"):
            content = entry.find(f"{{{_NS_ATOM}}}content")
            if content is None:
                continue
            props = content.find(f"{{{_NS_META}}}properties")
            if props is None:
                continue

            date_el = props.find(f"{{{_NS_DS}}}NEW_DATE")
            if date_el is None or not date_el.text:
                continue
            try:
                obs_date = date.fromisoformat(date_el.text[:10])
            except ValueError:
                continue

            for xml_tag, (field_name, tenor) in _TENOR_MAP.items():
                el = props.find(f"{{{_NS_DS}}}{xml_tag}")
                if el is None:
                    continue
                raw: float | None = None
                if el.text and el.text.strip():
                    try:
                        raw = float(el.text.strip())
                    except ValueError:
                        pass

                points.append(
                    MarketDataPoint(
                        as_of_date=obs_date,
                        field_name=field_name,
                        source_name="TREASURY_GOV",
                        source_url=source_url,
                        raw_value=raw,
                        normalized_value=raw,
                        unit="percent",
                        frequency="daily",
                        asset_class="rates",
                        region="US",
                        rating_bucket="na",
                        tenor_bucket=tenor,   # type: ignore[arg-type]
                        rebuild_grade="A",
                    )
                )
        return points
