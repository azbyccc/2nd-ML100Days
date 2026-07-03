"""Event-driven weekly-rebalance backtester.

Timeline for each rebalance week:
  1. Signal date    = last available trading day of the ISO week
                      (config.rebalance_weekday, default Friday).
  2. Execution date = the next trading day (Monday open) - this is when the
                      new top-10 actually starts earning/losing money and
                      when transaction costs are charged.
  3. Holding period = [execution date, day before the *next* execution date]
                      (or through the end of the data for the last week).

No lookahead: the score/eligibility/regime computation for a signal date only
ever uses price/turnover/benchmark rows up to and including that date.
"""

from __future__ import annotations

import pandas as pd

from config import StrategyConfig
from strategy import select_portfolio


def _weekly_signal_dates(dates: pd.DatetimeIndex) -> list[pd.Timestamp]:
    iso = dates.isocalendar()
    df = pd.DataFrame({"date": dates, "year": iso["year"].values, "week": iso["week"].values})
    return df.groupby(["year", "week"])["date"].max().sort_values().tolist()


class BacktestResult:
    def __init__(self):
        self.daily_returns = pd.Series(dtype=float)
        self.equity_curve = pd.Series(dtype=float)
        self.holdings_history: list[dict] = []   # one row per rebalance
        self.turnover_history: list[float] = []


def run_backtest(
    prices: pd.DataFrame,
    turnover: pd.DataFrame,
    benchmark: pd.Series,
    cfg: StrategyConfig,
) -> BacktestResult:
    dates = prices.index
    stock_daily_returns = prices.pct_change()
    signal_dates = _weekly_signal_dates(dates)
    min_lookback = max(cfg.lookback_days.values())

    date_pos = {d: i for i, d in enumerate(dates)}
    exec_dates = []
    for sd in signal_dates:
        pos = date_pos[sd]
        exec_dates.append(dates[pos + 1] if pos + 1 < len(dates) else None)

    result = BacktestResult()
    portfolio_returns = pd.Series(0.0, index=dates)

    buy_cost = cfg.buy_fee_bps / 10_000
    sell_cost = (cfg.sell_fee_bps + cfg.sell_tax_bps) / 10_000

    current_holdings: list[str] = []
    current_weights: dict[str, float] = {}
    first_exec_date = None

    for i, sd in enumerate(signal_dates):
        if date_pos[sd] < min_lookback:
            continue  # not enough history yet for the longest lookback window
        exec_date = exec_dates[i]
        if exec_date is None:
            break  # no trading day left to execute on (end of data)

        window_prices = prices.loc[:sd]
        window_turnover = turnover.loc[:sd]
        window_benchmark = benchmark.loc[:sd]

        new_holdings, scores, n_slots = select_portfolio(
            window_prices, window_turnover, window_benchmark, cfg, current_holdings
        )
        new_weights = {sid: 1.0 / n_slots for sid in new_holdings}

        turnover_frac = 0.0
        for sid in set(current_weights) | set(new_weights):
            delta = new_weights.get(sid, 0.0) - current_weights.get(sid, 0.0)
            if delta > 0:
                turnover_frac += delta * buy_cost
            elif delta < 0:
                turnover_frac += abs(delta) * sell_cost
        result.turnover_history.append(turnover_frac)
        result.holdings_history.append({
            "signal_date": sd,
            "execution_date": exec_date,
            "n_slots": n_slots,
            "holdings": list(new_holdings),
            "scores": scores.reindex(new_holdings).round(3).to_dict(),
        })

        next_exec_date = exec_dates[i + 1] if i + 1 < len(exec_dates) else None
        hold_end = dates[date_pos[next_exec_date] - 1] if next_exec_date is not None else dates[-1]
        period_dates = dates[(dates >= exec_date) & (dates <= hold_end)]

        if len(period_dates) > 0:
            if new_weights:
                w_vec = pd.Series(new_weights)
                period_ret = stock_daily_returns.loc[period_dates, list(new_weights)].fillna(0.0)
                port_ret = period_ret.mul(w_vec, axis=1).sum(axis=1)
            else:
                port_ret = pd.Series(0.0, index=period_dates)
            port_ret.iloc[0] -= turnover_frac  # one-time cost drag on execution day
            portfolio_returns.loc[period_dates] = port_ret

        if first_exec_date is None:
            first_exec_date = exec_date
        current_holdings, current_weights = new_holdings, new_weights

    result.daily_returns = (
        portfolio_returns.loc[first_exec_date:] if first_exec_date is not None else portfolio_returns.iloc[0:0]
    )
    result.equity_curve = (1.0 + result.daily_returns).cumprod()
    return result
