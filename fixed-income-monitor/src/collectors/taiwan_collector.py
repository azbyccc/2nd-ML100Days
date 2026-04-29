"""
Taiwan CBC (Central Bank of the Republic of China) yield collector.
Fetches TWD government bond yields from the CBC's open data portal.

Note: CBC provides some data via downloadable Excel/CSV files.
      Availability of machine-readable daily data is limited;
      some data may require manual extraction from PDF reports.
      This collector attempts the open-data endpoints first.
"""
import logging
from io import BytesIO, StringIO
from typing import Any

import pandas as pd
import requests

from .base_collector import BaseCollector

logger = logging.getLogger(__name__)

# CBC Open Data - Government Bond Yield Statistics
# Publicly accessible endpoint (check periodically for URL changes)
CBC_BOND_URL = (
    "https://www.cbc.gov.tw/public/data/FinancialStatistics/"
    "BondsInterestRate/BondsInterestRate.csv"
)

# Moex of Taiwan Stock Exchange bond yield reference
TWSE_BOND_URL = "https://www.twse.com.tw/en/bond/bondIndex.json"


class TaiwanCBCCollector(BaseCollector):
    """
    Fetches Taiwan government bond yields.
    Grade: C — partial coverage, endpoint stability not guaranteed.
    Manual verification recommended.
    """

    RATE_LIMIT_RPS = 0.1

    def _check_robots(self) -> bool:
        return self._robots_allows("https://www.cbc.gov.tw/")

    def fetch(self) -> pd.DataFrame:
        records: list[dict[str, Any]] = []

        # Attempt 1: CBC open data CSV
        cbc_records = self._fetch_cbc_csv()
        if cbc_records:
            records.extend(cbc_records)
            logger.info("Taiwan CBC CSV: %d records", len(cbc_records))
        else:
            logger.warning(
                "Taiwan CBC CSV unavailable. "
                "Consider manual download from https://www.cbc.gov.tw"
            )

        # Attempt 2: TWSE bond index (backup)
        twse_records = self._fetch_twse_bond()
        if twse_records:
            records.extend(twse_records)
            logger.info("TWSE bond: %d records", len(twse_records))

        if not records:
            logger.error(
                "Taiwan yield data unavailable from all sources. "
                "Grade C field — may require manual update."
            )
            return pd.DataFrame()

        df = pd.DataFrame(records)
        return self.mark_missing(df)

    def _fetch_cbc_csv(self) -> list[dict[str, Any]]:
        try:
            resp = self._get(CBC_BOND_URL)
            # CBC CSV may be encoded in Big5/UTF-8
            try:
                text = resp.content.decode("utf-8-sig")
            except UnicodeDecodeError:
                text = resp.content.decode("big5", errors="replace")

            df = pd.read_csv(StringIO(text), header=0)
            logger.debug("CBC CSV columns: %s", list(df.columns))

            records = []
            for _, row in df.iterrows():
                date_val = str(row.iloc[0]).strip() if len(row) > 0 else None
                if not date_val or date_val.lower() in ("nan", ""):
                    continue
                # Map columns by position — structure may vary
                tenor_map = {
                    "RATE_TW_2Y":  1,
                    "RATE_TW_5Y":  2,
                    "RATE_TW_10Y": 3,
                    "RATE_TW_20Y": 4,
                    "RATE_TW_30Y": 5,
                }
                for field_id, col_idx in tenor_map.items():
                    if col_idx < len(row):
                        try:
                            value = float(row.iloc[col_idx])
                        except (ValueError, TypeError):
                            value = None
                        records.append({
                            "series_id": field_id,
                            "name": f"Taiwan Govt Bond {field_id.split('_')[-1]}",
                            "date": date_val,
                            "value": value,
                            "unit": "percent",
                            "source": "TAIWAN_CBC",
                        })
            return records
        except Exception as exc:
            logger.debug("CBC CSV fetch failed: %s", exc)
            return []

    def _fetch_twse_bond(self) -> list[dict[str, Any]]:
        try:
            resp = self._get(TWSE_BOND_URL)
            data = resp.json()
            records = []
            # Parse TWSE bond index JSON (structure varies by API version)
            if isinstance(data, dict) and "data" in data:
                for row in data["data"]:
                    if len(row) >= 2:
                        records.append({
                            "series_id": "RATE_TW_BOND_IDX",
                            "name": "Taiwan Govt Bond Index",
                            "date": str(row[0]),
                            "value": float(row[1]) if row[1] else None,
                            "unit": "index_level",
                            "source": "TWSE",
                        })
            return records
        except Exception as exc:
            logger.debug("TWSE bond fetch failed: %s", exc)
            return []
