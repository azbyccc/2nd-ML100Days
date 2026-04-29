"""
Yahoo Finance Collector — Equity Indices, FX, Commodities
==========================================================
What it fetches (representative subset, Grade A/B):
  Equity:     S&P 500, Nikkei 225, DAX, FTSE 100, Hang Seng,
              Bovespa, KOSPI, TAIEX, ASX 200
  FX vs USD:  EUR, GBP, JPY, CHF, AUD, CNY, KRW, TWD, BRL, MXN
  Commodity:  WTI crude, Brent, Natural Gas, Gold, Silver

Output schema:  list[MarketDataPoint]
  unit:  "index_level" / "fx_rate" / "usd_per_unit"
  frequency: "daily"

Limitations:
  - yfinance wraps Yahoo Finance's UNOFFICIAL API; Yahoo ToS prohibits
    commercial use. Use for research only.
  - API structure changes without notice — pin yfinance version.
  - FX tickers return USD per foreign unit (EUR, GBP) OR USD per unit
    quoted as foreign/USD (JPY, KRW etc.). Check quote convention carefully.
  - Some EM/small-cap tickers may have data gaps (exchange closures,
    ticker changes, thin trading).
  - Futures tickers (CL=F, GC=F) roll monthly — historical series may
    show roll-date discontinuities. Use for level/trend only, not exact
    returns without roll adjustment.

Backup: For equity indices, consider Stooq (stooq.com) as free alternative.
        For FX, ECB SDMX API covers EUR pairs officially.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

from src.schema import MarketDataPoint
from .base_collector import BaseCollector

logger = logging.getLogger(__name__)

try:
    import yfinance as yf
    _HAS_YF = True
except ImportError:
    _HAS_YF = False
    logger.warning("yfinance not installed. Run: pip install yfinance")

_LOOKBACK_DAYS = 400

# ── Field registry ────────────────────────────────────────────────────────────
# (ticker, field_name, unit, asset_class, region, rating_bucket, tenor_bucket,
#  grade, notes)

FIELDS: list[dict[str, Any]] = [
    # Equity — North America
    dict(tk="^GSPC",    fn="EQ_SP500",   unit="index_level", ac="equity", rg="US",     rb="na", tb="na", gr="A"),
    dict(tk="^IXIC",    fn="EQ_NASDAQ",  unit="index_level", ac="equity", rg="US",     rb="na", tb="na", gr="A"),
    dict(tk="^RUT",     fn="EQ_RUSSELL2000", unit="index_level", ac="equity", rg="US", rb="na", tb="na", gr="A"),
    dict(tk="^GSPTSE",  fn="EQ_TSX",     unit="index_level", ac="equity", rg="CA",     rb="na", tb="na", gr="A"),
    # Equity — Europe
    dict(tk="^FTSE",    fn="EQ_FTSE100", unit="index_level", ac="equity", rg="UK",     rb="na", tb="na", gr="A"),
    dict(tk="^GDAXI",   fn="EQ_DAX",     unit="index_level", ac="equity", rg="EU",     rb="na", tb="na", gr="A"),
    dict(tk="^FCHI",    fn="EQ_CAC40",   unit="index_level", ac="equity", rg="EU",     rb="na", tb="na", gr="A"),
    dict(tk="^IBEX",    fn="EQ_IBEX",    unit="index_level", ac="equity", rg="EU",     rb="na", tb="na", gr="A"),
    # Equity — Latam
    dict(tk="^BVSP",    fn="EQ_BOVESPA", unit="index_level", ac="equity", rg="LATAM",  rb="na", tb="na", gr="A"),
    dict(tk="^MXX",     fn="EQ_IPC",     unit="index_level", ac="equity", rg="LATAM",  rb="na", tb="na", gr="A"),
    # Equity — Asia
    dict(tk="^N225",    fn="EQ_NIKKEI",  unit="index_level", ac="equity", rg="JP",     rb="na", tb="na", gr="A"),
    dict(tk="^HSI",     fn="EQ_HSI",     unit="index_level", ac="equity", rg="ASIA",   rb="na", tb="na", gr="A"),
    dict(tk="^KS11",    fn="EQ_KOSPI",   unit="index_level", ac="equity", rg="KR",     rb="na", tb="na", gr="A"),
    dict(tk="^TWII",    fn="EQ_TAIEX",   unit="index_level", ac="equity", rg="TW",     rb="na", tb="na", gr="A"),
    dict(tk="^AXJO",    fn="EQ_ASX200",  unit="index_level", ac="equity", rg="AU",     rb="na", tb="na", gr="A"),
    dict(tk="000001.SS",fn="EQ_SHCOMP",  unit="index_level", ac="equity", rg="ASIA",   rb="na", tb="na", gr="A",
         notes="Shanghai Composite — Chinese markets have exchange-specific holidays"),
    # FX vs USD
    dict(tk="EURUSD=X", fn="FX_EURUSD",  unit="fx_rate", ac="fx", rg="EU",     rb="na", tb="na", gr="A",
         notes="EUR per 1 USD (Bloomberg convention: EURUSD = EUR strength)"),
    dict(tk="GBPUSD=X", fn="FX_GBPUSD",  unit="fx_rate", ac="fx", rg="UK",     rb="na", tb="na", gr="A"),
    dict(tk="JPY=X",    fn="FX_USDJPY",  unit="fx_rate", ac="fx", rg="JP",     rb="na", tb="na", gr="A",
         notes="JPY per 1 USD"),
    dict(tk="CHF=X",    fn="FX_USDCHF",  unit="fx_rate", ac="fx", rg="EU",     rb="na", tb="na", gr="A"),
    dict(tk="AUDUSD=X", fn="FX_AUDUSD",  unit="fx_rate", ac="fx", rg="AU",     rb="na", tb="na", gr="A"),
    dict(tk="CNY=X",    fn="FX_USDCNY",  unit="fx_rate", ac="fx", rg="ASIA",   rb="na", tb="na", gr="A"),
    dict(tk="KRW=X",    fn="FX_USDKRW",  unit="fx_rate", ac="fx", rg="KR",     rb="na", tb="na", gr="A"),
    dict(tk="TWD=X",    fn="FX_USDTWD",  unit="fx_rate", ac="fx", rg="TW",     rb="na", tb="na", gr="B",
         notes="TWD NDF rate; onshore fixing from CBC is more accurate"),
    dict(tk="BRL=X",    fn="FX_USDBRL",  unit="fx_rate", ac="fx", rg="LATAM",  rb="na", tb="na", gr="A"),
    dict(tk="MXN=X",    fn="FX_USDMXN",  unit="fx_rate", ac="fx", rg="LATAM",  rb="na", tb="na", gr="A"),
    dict(tk="TRY=X",    fn="FX_USDTRY",  unit="fx_rate", ac="fx", rg="EEMA",   rb="na", tb="na", gr="A"),
    dict(tk="ZAR=X",    fn="FX_USDZAR",  unit="fx_rate", ac="fx", rg="EEMA",   rb="na", tb="na", gr="A"),
    # Commodities
    dict(tk="CL=F",     fn="CMD_WTI",    unit="usd_per_unit", ac="commodity", rg="GLOBAL", rb="na", tb="na", gr="A",
         notes="Front-month WTI futures; roll-date gaps possible"),
    dict(tk="BZ=F",     fn="CMD_BRENT",  unit="usd_per_unit", ac="commodity", rg="GLOBAL", rb="na", tb="na", gr="A"),
    dict(tk="GC=F",     fn="CMD_GOLD",   unit="usd_per_unit", ac="commodity", rg="GLOBAL", rb="na", tb="na", gr="A"),
    dict(tk="SI=F",     fn="CMD_SILVER", unit="usd_per_unit", ac="commodity", rg="GLOBAL", rb="na", tb="na", gr="A"),
    dict(tk="NG=F",     fn="CMD_NATGAS", unit="usd_per_unit", ac="commodity", rg="GLOBAL", rb="na", tb="na", gr="A"),
    dict(tk="ZC=F",     fn="CMD_CORN",   unit="usd_per_unit", ac="commodity", rg="GLOBAL", rb="na", tb="na", gr="A"),
    dict(tk="ZW=F",     fn="CMD_WHEAT",  unit="usd_per_unit", ac="commodity", rg="GLOBAL", rb="na", tb="na", gr="A"),
]


class YahooCollector(BaseCollector):
    """Fetches equity indices, FX rates, and commodity futures via yfinance."""

    SOURCE_NAME:    str   = "YAHOO_FINANCE"
    BASE_URL:       str   = "https://finance.yahoo.com"
    RATE_LIMIT_RPS: float = 0.3

    def fetch(self) -> list[MarketDataPoint]:
        if not _HAS_YF:
            logger.error("yfinance not available — install with: pip install yfinance")
            return []

        tickers = [f["tk"] for f in FIELDS]
        tk_to_field = {f["tk"]: f for f in FIELDS}
        start = (date.today() - timedelta(days=_LOOKBACK_DAYS)).strftime("%Y-%m-%d")

        logger.info("Yahoo Finance: downloading %d tickers from %s …", len(tickers), start)
        try:
            raw = yf.download(
                tickers=tickers,
                start=start,
                auto_adjust=True,
                progress=False,
                group_by="ticker",
                threads=True,
            )
        except Exception as exc:
            logger.error("yfinance download failed: %s", exc)
            return []

        return self.parse_download(raw, tk_to_field, tickers)

    @staticmethod
    def parse_download(
        raw,            # yfinance multi-ticker DataFrame
        tk_to_field: dict[str, dict],
        tickers: list[str],
    ) -> list[MarketDataPoint]:
        """
        Parse yfinance multi-ticker download into MarketDataPoint list.
        Exposed as static so tests can inject a pre-built DataFrame.
        """
        import pandas as pd
        points: list[MarketDataPoint] = []

        for ticker in tickers:
            field = tk_to_field.get(ticker)
            if field is None:
                continue
            try:
                # Multi-ticker download: raw[ticker]["Close"] or raw["Close"][ticker]
                if isinstance(raw.columns, pd.MultiIndex):
                    close_series = raw["Close"][ticker] if ticker in raw["Close"].columns else None
                else:
                    # Single-ticker case (shouldn't happen in batch, but handle it)
                    close_series = raw["Close"] if "Close" in raw.columns else None

                if close_series is None or close_series.empty:
                    logger.warning("Yahoo: no Close data for %s", ticker)
                    continue

                src_url = f"https://finance.yahoo.com/quote/{ticker}"
                for ts, val in close_series.items():
                    raw_val = float(val) if pd.notna(val) else None
                    obs_date = ts.date() if hasattr(ts, "date") else date.fromisoformat(str(ts)[:10])
                    points.append(
                        MarketDataPoint(
                            as_of_date=obs_date,
                            field_name=field["fn"],
                            source_name="YAHOO_FINANCE",
                            source_url=src_url,
                            raw_value=raw_val,
                            normalized_value=raw_val,
                            unit=field["unit"],           # type: ignore[arg-type]
                            frequency="daily",
                            asset_class=field["ac"],      # type: ignore[arg-type]
                            region=field["rg"],           # type: ignore[arg-type]
                            rating_bucket=field.get("rb", "na"),   # type: ignore[arg-type]
                            tenor_bucket=field.get("tb", "na"),    # type: ignore[arg-type]
                            rebuild_grade=field.get("gr", "A"),    # type: ignore[arg-type]
                            notes=field.get("notes", ""),
                        )
                    )
            except Exception as exc:
                logger.warning("Yahoo parse error for %s: %s", ticker, exc)

        logger.info("Yahoo Finance parsed: %d points across %d fields",
                    len(points), len({p.field_name for p in points}))
        return points
