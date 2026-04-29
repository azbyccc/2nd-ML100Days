"""
Tests for YahooCollector.parse_download()

Fully offline — injects a pre-built pandas MultiIndex DataFrame.
No network calls. No yfinance dependency during test.
Run: pytest tests/test_yahoo.py -v
"""
from datetime import date

import pandas as pd
import pytest

from src.schema import MarketDataPoint
from src.collectors.yahoo_collector import YahooCollector, FIELDS


def _make_mock_download(ticker: str, dates: list[str], closes: list[float]) -> pd.DataFrame:
    """Build a multi-index DataFrame mimicking yfinance batch download output."""
    idx = pd.to_datetime(dates)
    arrays = [
        pd.Index(["Close"] * len(dates), name="Price"),
        pd.Index([ticker] * len(dates), name="Ticker"),
    ]
    cols = pd.MultiIndex.from_arrays([["Close"] * len(dates), [ticker] * len(dates)],
                                     names=["Price", "Ticker"])
    # Build a proper MultiIndex column DataFrame
    close_series = pd.Series(closes, index=idx, name=ticker)
    df = pd.DataFrame({"Close": {ticker: close_series}})
    # Flatten to standard yfinance format
    df_out = pd.DataFrame({"Close": close_series})
    df_out.columns = pd.MultiIndex.from_tuples([("Close", ticker)], names=["Price", "Ticker"])
    return df_out


class TestYahooParseDownload:
    def _sp500_field(self):
        return next(f for f in FIELDS if f["fn"] == "EQ_SP500")

    def test_returns_list_of_points(self):
        ticker = "^GSPC"
        dates  = ["2026-04-22", "2026-04-23", "2026-04-24"]
        closes = [5100.0, 5120.0, 5095.0]

        raw = _make_mock_download(ticker, dates, closes)
        tk_to_field = {ticker: self._sp500_field()}

        pts = YahooCollector.parse_download(raw, tk_to_field, [ticker])
        assert isinstance(pts, list)
        assert all(isinstance(p, MarketDataPoint) for p in pts)

    def test_correct_count(self):
        ticker = "^GSPC"
        dates  = ["2026-04-22", "2026-04-23", "2026-04-24"]
        closes = [5100.0, 5120.0, 5095.0]
        raw = _make_mock_download(ticker, dates, closes)
        pts = YahooCollector.parse_download(raw, {ticker: self._sp500_field()}, [ticker])
        assert len(pts) == 3

    def test_value_parsed(self):
        ticker = "^GSPC"
        raw = _make_mock_download(ticker, ["2026-04-28"], [5200.5])
        pts = YahooCollector.parse_download(raw, {ticker: self._sp500_field()}, [ticker])
        assert len(pts) == 1
        assert pts[0].normalized_value == pytest.approx(5200.5)
        assert pts[0].as_of_date == date(2026, 4, 28)

    def test_schema_for_equity(self):
        ticker = "^GSPC"
        raw = _make_mock_download(ticker, ["2026-04-28"], [5200.0])
        pts = YahooCollector.parse_download(raw, {ticker: self._sp500_field()}, [ticker])
        p = pts[0]
        assert p.field_name    == "EQ_SP500"
        assert p.asset_class   == "equity"
        assert p.region        == "US"
        assert p.unit          == "index_level"
        assert p.source_name   == "YAHOO_FINANCE"
        assert p.rebuild_grade == "A"

    def test_schema_for_fx(self):
        ticker = "EURUSD=X"
        field  = next(f for f in FIELDS if f["fn"] == "FX_EURUSD")
        raw    = _make_mock_download(ticker, ["2026-04-28"], [1.0850])
        pts    = YahooCollector.parse_download(raw, {ticker: field}, [ticker])
        p = pts[0]
        assert p.field_name    == "FX_EURUSD"
        assert p.asset_class   == "fx"
        assert p.unit          == "fx_rate"

    def test_schema_for_commodity(self):
        ticker = "GC=F"
        field  = next(f for f in FIELDS if f["fn"] == "CMD_GOLD")
        raw    = _make_mock_download(ticker, ["2026-04-28"], [3350.0])
        pts    = YahooCollector.parse_download(raw, {ticker: field}, [ticker])
        p = pts[0]
        assert p.field_name    == "CMD_GOLD"
        assert p.asset_class   == "commodity"
        assert p.unit          == "usd_per_unit"

    def test_all_registered_fields_have_grade(self):
        for f in FIELDS:
            assert f.get("gr") in ("A", "B"), \
                f"Field {f['fn']} has unexpected grade: {f.get('gr')}"

    def test_no_d_grade_fields_present(self):
        d_grade = [f for f in FIELDS if f.get("gr") == "D"]
        assert d_grade == [], f"D-grade fields should not be in Yahoo collector: {d_grade}"
