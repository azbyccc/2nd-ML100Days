"""
Tests for CBOECollector.parse_csv()

Fully offline — uses fixture CSV. No HTTP calls.
Run: pytest tests/test_cboe.py -v
"""
from datetime import date
from pathlib import Path

import pytest

from src.schema import MarketDataPoint
from src.collectors.cboe_collector import CBOECollector

FIXTURE = Path(__file__).parent / "fixtures" / "cboe_vix.csv"


@pytest.fixture
def csv_text():
    return FIXTURE.read_text(encoding="utf-8")


class TestCBOEParseCsv:
    def test_returns_list_of_points(self, csv_text):
        pts = CBOECollector.parse_csv(csv_text, "http://example.com")
        assert isinstance(pts, list)
        assert all(isinstance(p, MarketDataPoint) for p in pts)

    def test_correct_count(self, csv_text):
        pts = CBOECollector.parse_csv(csv_text, "http://example.com")
        assert len(pts) == 5

    def test_latest_close_value(self, csv_text):
        pts = CBOECollector.parse_csv(csv_text, "http://example.com")
        latest = [p for p in pts if p.as_of_date == date(2026, 4, 28)]
        assert len(latest) == 1
        assert latest[0].normalized_value == pytest.approx(17.70)

    def test_schema_fields(self, csv_text):
        pts = CBOECollector.parse_csv(csv_text, "http://example.com")
        p = pts[0]
        assert p.field_name    == "VIX"
        assert p.source_name   == "CBOE"
        assert p.unit          == "index_level"
        assert p.asset_class   == "equity"
        assert p.region        == "US"
        assert p.rebuild_grade == "A"

    def test_all_points_have_same_field_name(self, csv_text):
        pts = CBOECollector.parse_csv(csv_text, "http://example.com")
        assert all(p.field_name == "VIX" for p in pts)

    def test_empty_csv_returns_empty(self):
        pts = CBOECollector.parse_csv("", "http://example.com")
        assert pts == []
