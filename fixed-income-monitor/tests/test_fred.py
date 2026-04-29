"""
Tests for FREDCollector.parse_observations()

Tests are fully offline — no HTTP calls made.
Run: pytest tests/test_fred.py -v
"""
import json
from datetime import date
from pathlib import Path

import pytest

from src.schema import MarketDataPoint
from src.collectors.fred_collector import FREDCollector, FIELDS

FIXTURE = Path(__file__).parent / "fixtures" / "fred_observations.json"

# A representative field entry (US 10Y Treasury)
_FIELD_10Y = {
    "sid": "DGS10",
    "fn":  "US_TREASURY_10Y",
    "unit":"percent",
    "ac":  "rates",
    "rg":  "US",
    "rb":  "na",
    "tb":  "10y",
    "gr":  "A",
}

_FIELD_HY = {
    "sid": "BAMLH0A0HYM2",
    "fn":  "US_HY_OAS",
    "unit":"basis_points",
    "ac":  "credit",
    "rg":  "US",
    "rb":  "hy",
    "tb":  "na",
    "gr":  "A",
}


@pytest.fixture
def observations():
    with open(FIXTURE) as f:
        return json.load(f)["observations"]


class TestFREDParseObservations:
    def test_returns_list_of_market_data_points(self, observations):
        pts = FREDCollector.parse_observations(observations, _FIELD_10Y, "http://example.com")
        assert isinstance(pts, list)
        assert all(isinstance(p, MarketDataPoint) for p in pts)

    def test_correct_count(self, observations):
        pts = FREDCollector.parse_observations(observations, _FIELD_10Y, "http://example.com")
        # 5 observations in fixture
        assert len(pts) == 5

    def test_missing_value_is_none(self, observations):
        pts = FREDCollector.parse_observations(observations, _FIELD_10Y, "http://example.com")
        # Index 3 has value "." — should parse to None
        missing = [p for p in pts if p.as_of_date == date(2026, 4, 25)]
        assert len(missing) == 1
        assert missing[0].normalized_value is None
        assert missing[0].raw_value is None

    def test_valid_value_parsed(self, observations):
        pts = FREDCollector.parse_observations(observations, _FIELD_10Y, "http://example.com")
        latest = [p for p in pts if p.as_of_date == date(2026, 4, 28)]
        assert len(latest) == 1
        assert latest[0].normalized_value == pytest.approx(4.28)

    def test_schema_fields_set_correctly(self, observations):
        pts = FREDCollector.parse_observations(observations, _FIELD_10Y, "http://example.com")
        p = pts[0]
        assert p.field_name    == "US_TREASURY_10Y"
        assert p.source_name   == "FRED"
        assert p.unit          == "percent"
        assert p.asset_class   == "rates"
        assert p.region        == "US"
        assert p.tenor_bucket  == "10y"
        assert p.rebuild_grade == "A"

    def test_credit_field_uses_basis_points(self, observations):
        pts = FREDCollector.parse_observations(observations, _FIELD_HY, "http://example.com")
        p = [p for p in pts if p.normalized_value is not None][0]
        assert p.unit          == "basis_points"
        assert p.asset_class   == "credit"
        assert p.rating_bucket == "hy"

    def test_field_name_uppercased(self, observations):
        field = dict(_FIELD_10Y, fn="us_treasury_10y")  # lowercase input
        pts = FREDCollector.parse_observations(observations, field, "http://example.com")
        assert pts[0].field_name == "US_TREASURY_10Y"

    def test_all_registered_fields_have_required_keys(self):
        required = {"sid", "fn", "unit", "ac", "rg"}
        for f in FIELDS:
            missing = required - set(f.keys())
            assert not missing, f"Field {f.get('fn')} missing keys: {missing}"
