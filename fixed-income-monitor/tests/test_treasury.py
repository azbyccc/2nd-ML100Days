"""
Tests for TreasuryGovCollector.parse_xml()

Fully offline — uses fixture XML. No HTTP calls.
Run: pytest tests/test_treasury.py -v
"""
from datetime import date
from pathlib import Path

import pytest

from src.schema import MarketDataPoint
from src.collectors.treasury_collector import TreasuryGovCollector

FIXTURE = Path(__file__).parent / "fixtures" / "treasury_xml_snippet.xml"


@pytest.fixture
def xml_text():
    return FIXTURE.read_text(encoding="utf-8")


class TestTreasuryParseXml:
    def test_returns_list_of_points(self, xml_text):
        pts = TreasuryGovCollector.parse_xml(xml_text, "http://example.com")
        assert isinstance(pts, list)
        assert all(isinstance(p, MarketDataPoint) for p in pts)

    def test_correct_number_of_points(self, xml_text):
        pts = TreasuryGovCollector.parse_xml(xml_text, "http://example.com")
        # Fixture has 2 entries × 4 tenors = 8 points
        assert len(pts) == 8

    def test_dates_parsed_correctly(self, xml_text):
        pts = TreasuryGovCollector.parse_xml(xml_text, "http://example.com")
        dates = {p.as_of_date for p in pts}
        assert date(2026, 4, 28) in dates
        assert date(2026, 4, 27) in dates

    def test_10y_value_for_latest_date(self, xml_text):
        pts = TreasuryGovCollector.parse_xml(xml_text, "http://example.com")
        ten_yr = [p for p in pts if p.field_name == "US_TREASURY_10Y"
                  and p.as_of_date == date(2026, 4, 28)]
        assert len(ten_yr) == 1
        assert ten_yr[0].normalized_value == pytest.approx(4.32)

    def test_schema_fields(self, xml_text):
        pts = TreasuryGovCollector.parse_xml(xml_text, "http://example.com")
        p = pts[0]
        assert p.source_name   == "TREASURY_GOV"
        assert p.unit          == "percent"
        assert p.asset_class   == "rates"
        assert p.region        == "US"
        assert p.rebuild_grade == "A"
        assert p.rating_bucket == "na"

    def test_tenor_bucket_mapped(self, xml_text):
        pts = TreasuryGovCollector.parse_xml(xml_text, "http://example.com")
        tenors = {p.tenor_bucket for p in pts}
        assert "2y"  in tenors
        assert "10y" in tenors
        assert "30y" in tenors

    def test_invalid_xml_returns_empty(self):
        pts = TreasuryGovCollector.parse_xml("<bad xml>{{{{", "http://example.com")
        assert pts == []

    def test_empty_xml_returns_empty(self):
        pts = TreasuryGovCollector.parse_xml("", "http://example.com")
        assert pts == []
