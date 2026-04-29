"""
Tests for ECBCollector.parse_csv()

Fully offline — uses fixture CSV. No HTTP calls.
Run: pytest tests/test_ecb.py -v
"""
from datetime import date
from pathlib import Path

import pytest

from src.schema import MarketDataPoint
from src.collectors.ecb_collector import ECBCollector

FIXTURE = Path(__file__).parent / "fixtures" / "ecb_csv_snippet.txt"

_FIELD_EURIBOR3M = {
    "ds": "FM",
    "key": "B.U2.EUR.RT0.MM.EURIBOR3MD_.HSTA",
    "fn":  "EU_EURIBOR_3M",
    "unit":"percent",
    "rb":  "na",
    "tb":  "3m",
    "gr":  "A",
}


@pytest.fixture
def csv_text():
    return FIXTURE.read_text(encoding="utf-8")


class TestECBParseCsv:
    def test_returns_list_of_points(self, csv_text):
        pts = ECBCollector.parse_csv(csv_text, _FIELD_EURIBOR3M, "http://example.com")
        assert isinstance(pts, list)
        assert all(isinstance(p, MarketDataPoint) for p in pts)

    def test_correct_count(self, csv_text):
        pts = ECBCollector.parse_csv(csv_text, _FIELD_EURIBOR3M, "http://example.com")
        # 5 rows in fixture
        assert len(pts) == 5

    def test_value_parsed(self, csv_text):
        pts = ECBCollector.parse_csv(csv_text, _FIELD_EURIBOR3M, "http://example.com")
        latest = [p for p in pts if p.as_of_date == date(2026, 4, 28)]
        assert len(latest) == 1
        assert latest[0].normalized_value == pytest.approx(2.535)

    def test_schema_fields(self, csv_text):
        pts = ECBCollector.parse_csv(csv_text, _FIELD_EURIBOR3M, "http://example.com")
        p = pts[0]
        assert p.field_name    == "EU_EURIBOR_3M"
        assert p.source_name   == "ECB"
        assert p.unit          == "percent"
        assert p.asset_class   == "rates"
        assert p.region        == "EU"
        assert p.tenor_bucket  == "3m"
        assert p.rebuild_grade == "A"

    def test_empty_csv_returns_empty(self):
        pts = ECBCollector.parse_csv("", _FIELD_EURIBOR3M, "http://example.com")
        assert pts == []

    def test_header_only_returns_empty(self):
        header = "KEY,FREQ,TIME_PERIOD,OBS_VALUE"
        pts = ECBCollector.parse_csv(header, _FIELD_EURIBOR3M, "http://example.com")
        assert pts == []

    def test_missing_obs_value_column_returns_empty(self):
        bad_csv = "KEY,FREQ,TIME_PERIOD\nfoo,B,2026-04-28"
        pts = ECBCollector.parse_csv(bad_csv, _FIELD_EURIBOR3M, "http://example.com")
        assert pts == []
