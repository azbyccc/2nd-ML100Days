"""End-to-end demo of the Taiwan Top-10 Momentum strategy.

Uses `SyntheticDataSource` (reproducible fake data, no network needed) so the
whole pipeline - scoring, eligibility filters, hysteresis selection, weekly
rebalancing, transaction costs, and performance metrics - can be verified in
any environment, including offline/sandboxed ones.

To run on real Taiwan market data, swap `SyntheticDataSource` for
`FinMindDataSource`, `YahooFinanceDataSource`, or `CSVDataSource` from
`data_source.py` (see README.md for setup notes) - nothing else changes.
"""

from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from backtest import run_backtest
from config import StrategyConfig
from data_source import SyntheticDataSource
from metrics import format_summary, summarize
from strategy import select_portfolio


def main():
    cfg = StrategyConfig()
    source = SyntheticDataSource(n_stocks=120, seed=42)

    start, end = "2021-01-01", "2024-12-31"
    universe = source.get_universe()
    prices = source.get_prices(universe, start, end)
    turnover = source.get_turnover(universe, start, end)
    benchmark = source.get_benchmark(start, end)

    print(f"Universe: {len(universe)} synthetic tickers, {prices.index[0].date()} .. {prices.index[-1].date()}\n")

    result = run_backtest(prices, turnover, benchmark, cfg)
    strategy_summary = summarize(result.daily_returns, result.turnover_history)

    bench_ret = benchmark.pct_change().reindex(result.daily_returns.index).fillna(0.0)
    bench_summary = summarize(bench_ret)

    print(format_summary(strategy_summary, "Top-10 Momentum (weekly rebalance)"))
    print()
    print(format_summary(bench_summary, "Benchmark (equal-weight universe)"))

    # Latest week's picks - what you'd actually trade if this ran live today
    latest_holdings, latest_scores, n_slots = select_portfolio(
        prices, turnover, benchmark, cfg, current_holdings=result.holdings_history[-1]["holdings"]
    )
    print(f"\n== Latest selection ({n_slots} slots) as of {prices.index[-1].date()} ==")
    picks = latest_scores.reindex(latest_holdings).sort_values(ascending=False)
    for rank, (sid, score) in enumerate(picks.items(), start=1):
        print(f"{rank:2d}. {sid}  score={score:.3f}")

    # Save an equity curve chart + holdings history CSV under output/
    import os
    out_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(out_dir, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10, 5))
    result.equity_curve.rename("Top-10 Momentum").plot(ax=ax)
    (1 + bench_ret).cumprod().rename("Benchmark").plot(ax=ax)
    ax.set_title("Taiwan Top-10 Momentum (weekly rebalance) - synthetic-data demo")
    ax.set_ylabel("Growth of 1")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "equity_curve.png"), dpi=120)
    print(f"\nSaved equity_curve.png to {out_dir}")

    import pandas as pd
    rows = []
    for h in result.holdings_history:
        rows.append({
            "signal_date": h["signal_date"].date(),
            "execution_date": h["execution_date"].date(),
            "n_slots": h["n_slots"],
            "holdings": ",".join(h["holdings"]),
        })
    pd.DataFrame(rows).to_csv(os.path.join(out_dir, "holdings_history.csv"), index=False)
    print(f"Saved holdings_history.csv to {out_dir}")


if __name__ == "__main__":
    main()
