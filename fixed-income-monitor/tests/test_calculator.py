"""
Tests for PerformanceCalculator

Uses a temporary HistoryStore with synthetic data. No HTTP calls.
Run: pytest tests/test_calculator.py -v
"""
import tempfile
from datetime import date, timedelta

import pytest

from src.schema import MarketDataPoint, PerformanceSnapshot
from src.storage import HistoryStore
from src.calculators import PerformanceCalculator


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_point(
    field_name: str,
    as_of_date: date,
    value: float,
    asset_class: str = "rates",
    unit: str = "percent",
) -> MarketDataPoint:
    return MarketDataPoint(
        as_of_date=as_of_date,
        field_name=field_name,
        source_name="TEST",
        source_url="http://test",
        raw_value=value,
        normalized_value=value,
        unit=unit,           # type: ignore[arg-type]
        frequency="daily",
        asset_class=asset_class,  # type: ignore[arg-type]
        region="US",
        rebuild_grade="A",
    )


def _populate_store(store: HistoryStore, field: str, start: date, days: int, base: float,
                    asset_class: str = "rates", unit: str = "percent") -> list[MarketDataPoint]:
    """Fill store with daily values: base + 0.01 * i for business days."""
    pts = []
    d = start
    for i in range(days):
        # Skip weekends
        while d.weekday() >= 5:
            d += timedelta(days=1)
        pt = _make_point(field, d, round(base + 0.01 * i, 4), asset_class, unit)
        pts.append(pt)
        d += timedelta(days=1)
    store.append([p.to_dict() for p in pts])
    return pts


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestPerformanceCalculator:
    @pytest.fixture
    def tmp_store(self):
        with tempfile.TemporaryDirectory() as d:
            yield HistoryStore(d)

    def test_d1_absolute_change(self, tmp_store):
        """D1 for a rates field should be current - prior business day value."""
        today = date(2026, 4, 28)  # Tuesday
        prior = date(2026, 4, 27)  # Monday

        pt_prior = _make_point("US_10Y", prior, 4.25)
        pt_today = _make_point("US_10Y", today, 4.30)
        tmp_store.append([pt_prior.to_dict(), pt_today.to_dict()])

        calc = PerformanceCalculator(tmp_store, as_of=today)
        snaps = calc.compute([pt_today])

        assert len(snaps) == 1
        snap = snaps[0]
        assert snap.d1 == pytest.approx(0.05, abs=1e-4)

    def test_d1_is_none_when_no_prior(self, tmp_store):
        """D1 should be None when there's no prior day in store."""
        today = date(2026, 4, 28)
        pt = _make_point("NEW_FIELD", today, 5.0)
        tmp_store.append([pt.to_dict()])

        calc = PerformanceCalculator(tmp_store, as_of=today)
        snaps = calc.compute([pt])

        assert snaps[0].d1 is None

    def test_ytd_reference_is_dec31(self, tmp_store):
        """YTD should use Dec 31 of prior year as reference."""
        dec31 = date(2025, 12, 31)
        today = date(2026, 4, 28)

        pt_dec31 = _make_point("US_10Y", dec31, 4.00)
        pt_today = _make_point("US_10Y", today, 4.32)
        tmp_store.append([pt_dec31.to_dict(), pt_today.to_dict()])

        calc = PerformanceCalculator(tmp_store, as_of=today)
        snaps = calc.compute([pt_today])

        assert snaps[0].ytd == pytest.approx(0.32, abs=1e-4)

    def test_equity_uses_percent_return(self, tmp_store):
        """Equity D1 should be percent return, not absolute change."""
        today = date(2026, 4, 28)
        prior = date(2026, 4, 27)

        pt_prior = _make_point("EQ_SP500", prior, 5000.0, asset_class="equity", unit="index_level")
        pt_today = _make_point("EQ_SP500", today, 5100.0, asset_class="equity", unit="index_level")
        tmp_store.append([pt_prior.to_dict(), pt_today.to_dict()])

        calc = PerformanceCalculator(tmp_store, as_of=today)
        snaps = calc.compute([pt_today])

        # Expect percent return: (5100/5000 - 1) * 100 = 2.0%
        assert snaps[0].d1 == pytest.approx(2.0, abs=0.001)

    def test_pct_rank_1y_is_50_for_median(self, tmp_store):
        """
        If today's value is exactly the median of a 100-day uniform series,
        the 1Y percentile rank should be ~50%.
        """
        start = date(2026, 4, 28) - timedelta(days=200)
        pts = _populate_store(tmp_store, "TEST_RATE", start, 150, base=3.0)
        # Today's value is the middle of the range
        median_val = pts[len(pts) // 2].normalized_value
        today_pt = _make_point("TEST_RATE", date(2026, 4, 28), median_val)
        tmp_store.append([today_pt.to_dict()])

        calc = PerformanceCalculator(tmp_store, as_of=date(2026, 4, 28))
        snaps = calc.compute([today_pt])

        # Allow ±15% tolerance for median percentile rank
        assert snaps[0].pct_rank_1y is not None
        assert 35 <= snaps[0].pct_rank_1y <= 65

    def test_pct_rank_none_when_insufficient_history(self, tmp_store):
        """pct_rank_1y should be None if < 5 data points in past year."""
        today = date(2026, 4, 28)
        pt = _make_point("SPARSE", today, 5.0)
        tmp_store.append([pt.to_dict()])

        calc = PerformanceCalculator(tmp_store, as_of=today)
        snaps = calc.compute([pt])

        assert snaps[0].pct_rank_1y is None

    def test_missing_value_gives_none_changes(self, tmp_store):
        """If today's value is None (missing), all changes should be None."""
        today = date(2026, 4, 28)
        prior = date(2026, 4, 27)
        pt_prior = _make_point("US_10Y", prior, 4.25)
        pt_today = _make_point("US_10Y", today, 0.0)
        pt_today = pt_today.model_copy(update={"normalized_value": None})
        tmp_store.append([pt_prior.to_dict()])

        calc = PerformanceCalculator(tmp_store, as_of=today)
        snaps = calc.compute([pt_today])

        snap = snaps[0]
        assert snap.d1 is None
        assert snap.wtd is None

    def test_snapshot_preserves_point_metadata(self, tmp_store):
        """PerformanceSnapshot must carry the original MarketDataPoint through."""
        today = date(2026, 4, 28)
        pt = _make_point("US_SOFR", today, 5.33)
        tmp_store.append([pt.to_dict()])

        calc = PerformanceCalculator(tmp_store, as_of=today)
        snaps = calc.compute([pt])

        assert snaps[0].point.field_name  == "US_SOFR"
        assert snaps[0].point.source_name == "TEST"
        assert snaps[0].point.rebuild_grade == "A"
