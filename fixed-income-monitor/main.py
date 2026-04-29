"""
Fixed Income Market Monitor — Non-Bloomberg replacement
=======================================================
Usage:
    python main.py                         # run all sources for today
    python main.py --sources fred,yahoo    # run specific sources
    python main.py --date 2026-04-25       # run for a specific date
    python main.py --list-sources          # show available sources
    python main.py --no-xlsx               # skip Excel output
    python main.py --prune                 # clean old history (>400d)

Environment variables:
    FRED_API_KEY   free FRED key from https://fred.stlouisfed.org/

Pipeline:
    1. Collect → list[MarketDataPoint]
    2. Store   → append to data/history/*.parquet (or .csv fallback)
    3. Compute → list[PerformanceSnapshot]  (D1/WTD/MTD/YTD from history)
    4. Export  → data/processed/fi_monitor_YYYYMMDD.{csv,xlsx}
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, datetime
from pathlib import Path

# ── logging setup (before any src imports) ────────────────────────────────────

def _setup_logging(level: str = "INFO") -> None:
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    tag = datetime.now().strftime("%Y%m%d_%H%M%S")
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=fmt,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(f"logs/run_{tag}.log", encoding="utf-8"),
        ],
    )
    # Quieten noisy libraries
    for noisy in ("urllib3", "yfinance", "peewee", "chardet"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


logger = logging.getLogger(__name__)

# ── Imports ───────────────────────────────────────────────────────────────────

sys.path.insert(0, str(Path(__file__).parent))

from src.collectors import (
    FREDCollector,
    TreasuryGovCollector,
    YahooCollector,
    ECBCollector,
    CBOECollector,
)
from src.schema import MarketDataPoint
from src.storage import HistoryStore
from src.calculators import PerformanceCalculator
from src.output import ReportBuilder

# ── Collector registry ────────────────────────────────────────────────────────

REGISTRY: dict[str, tuple[type, str]] = {
    "fred":     (FREDCollector,       "FRED API — US Treasuries, TIPS, BEI, ICE BofA credit (Grade A)"),
    "treasury": (TreasuryGovCollector,"Treasury.gov — Official US yield curve (Grade A)"),
    "yahoo":    (YahooCollector,      "Yahoo Finance — Equity indices, FX, Commodities (Grade A/B)"),
    "ecb":      (ECBCollector,        "ECB SDMX — Euribor, EUR yield curve (Grade A)"),
    "cboe":     (CBOECollector,       "CBOE — VIX daily history (Grade A)"),
}

_DEFAULT_SOURCES = list(REGISTRY.keys())


# ── Pipeline ──────────────────────────────────────────────────────────────────

def run(
    sources:    list[str],
    as_of:      date,
    write_xlsx: bool = True,
    history_dir: str = "data/history",
    output_dir:  str = "data/processed",
) -> dict[str, Path]:

    store   = HistoryStore(history_dir)
    builder = ReportBuilder(output_dir)

    # ── 1. Collect ────────────────────────────────────────────────────────────
    all_points: list[MarketDataPoint] = []
    for src_key in sources:
        if src_key not in REGISTRY:
            logger.warning("Unknown source '%s' — skipped", src_key)
            continue

        CollectorClass, desc = REGISTRY[src_key]
        logger.info("▶ %s", desc)
        try:
            collector = CollectorClass()
            pts = collector.collect()
            logger.info("  ✓ collected %d points from %d fields",
                        len(pts), len({p.field_name for p in pts}))
            all_points.extend(pts)
        except Exception as exc:
            logger.error("  ✗ %s failed: %s", src_key, exc, exc_info=True)

    if not all_points:
        logger.error("No data collected — exiting.")
        return {}

    # ── 2. Store ──────────────────────────────────────────────────────────────
    records = [p.to_dict() for p in all_points]
    added   = store.append(records)
    total_added = sum(added.values())
    logger.info("▶ Stored %d new rows across %d fields", total_added, len(added))

    # ── 3. Compute performance ────────────────────────────────────────────────
    # Filter to today's (or most recent) points for snapshot
    today_pts = [p for p in all_points if abs((p.as_of_date - as_of).days) <= 1]
    if not today_pts:
        logger.warning("No points for %s — computing from full store", as_of)
    calc      = PerformanceCalculator(store, as_of=as_of)
    snapshots = calc.compute(today_pts) if today_pts else calc.compute_all_from_store()
    logger.info("▶ Computed performance for %d fields", len(snapshots))

    # ── 4. Export ─────────────────────────────────────────────────────────────
    outputs = builder.build(snapshots, as_of=as_of, write_xlsx=write_xlsx)

    # ── Summary ───────────────────────────────────────────────────────────────
    _print_summary(snapshots)
    return outputs


def _print_summary(snapshots) -> None:
    total   = len(snapshots)
    missing = sum(1 for s in snapshots if s.point.is_missing())
    no_d1   = sum(1 for s in snapshots if s.d1 is None)
    print("\n" + "═" * 62)
    print(f"  Fixed Income Monitor — Summary")
    print("═" * 62)
    print(f"  Fields in snapshot  : {total}")
    print(f"  Missing value       : {missing}")
    print(f"  No D1 change (new)  : {no_d1}")

    by_class: dict[str, int] = {}
    for s in snapshots:
        ac = s.point.asset_class
        by_class[ac] = by_class.get(ac, 0) + 1
    print(f"  By asset class:")
    for ac, n in sorted(by_class.items()):
        print(f"    {ac:<15}: {n}")
    print("═" * 62 + "\n")


# ── CLI ───────────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Fixed Income Market Monitor — Non-Bloomberg replacement",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--date",    type=str, default=None,
                   help="As-of date YYYY-MM-DD (default: today)")
    p.add_argument("--sources", type=str, default=",".join(_DEFAULT_SOURCES),
                   help=f"Comma-separated list. Available: {', '.join(REGISTRY)}")
    p.add_argument("--no-xlsx", action="store_true", help="Skip Excel output")
    p.add_argument("--prune",   action="store_true", help="Prune history > 400 days")
    p.add_argument("--log-level", default="INFO",
                   choices=["DEBUG","INFO","WARNING","ERROR"])
    p.add_argument("--list-sources", action="store_true",
                   help="List available sources and exit")
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    _setup_logging(args.log_level)

    if args.list_sources:
        print("\nAvailable sources:")
        for key, (_, desc) in REGISTRY.items():
            print(f"  {key:<12} {desc}")
        return

    if args.prune:
        HistoryStore("data/history").prune(keep_days=400)
        return

    as_of = date.today()
    if args.date:
        try:
            as_of = datetime.strptime(args.date, "%Y-%m-%d").date()
        except ValueError:
            logger.error("Invalid date: %s (expected YYYY-MM-DD)", args.date)
            sys.exit(1)

    sources = [s.strip() for s in args.sources.split(",") if s.strip()]

    logger.info("═" * 62)
    logger.info("Fixed Income Market Monitor  as_of=%s", as_of)
    logger.info("Sources: %s", ", ".join(sources))
    logger.info("═" * 62)

    outputs = run(
        sources=sources,
        as_of=as_of,
        write_xlsx=not args.no_xlsx,
    )

    if outputs:
        print("Output files:")
        for fmt, path in outputs.items():
            print(f"  {fmt.upper():<6} → {path}")
    else:
        print("No output generated.")
        sys.exit(1)


if __name__ == "__main__":
    main()
