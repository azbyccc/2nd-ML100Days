"""Composite-momentum "top strong stocks" selection logic."""

from __future__ import annotations

import numpy as np
import pandas as pd

from config import StrategyConfig


def compute_momentum_scores(prices: pd.DataFrame, cfg: StrategyConfig) -> pd.Series:
    """Cross-sectional composite momentum score as of the last row of `prices`.

    For each lookback window, compute each stock's simple return, cross-
    sectionally rank it (percentile 0-1), then take the weighted average of
    the ranks. Ranking (rather than raw weighted returns) keeps a single
    outlier name from dominating the score and puts every factor on the same
    scale.
    """
    last = prices.iloc[-1]
    ranks = {}
    for name, n_days in cfg.lookback_days.items():
        if len(prices) <= n_days:
            continue
        past = prices.iloc[-n_days - 1]
        ret = last / past - 1.0
        ranks[name] = ret.rank(pct=True, na_option="keep")

    if not ranks:
        return pd.Series(dtype=float)

    weights = {k: cfg.lookback_weights.get(k, 0.0) for k in ranks}
    total_w = sum(weights.values()) or 1.0

    score = sum(ranks[k] * (weights[k] / total_w) for k in ranks)
    return score.rename("score")


def apply_eligibility_filters(
    prices: pd.DataFrame, turnover: pd.DataFrame, cfg: StrategyConfig
) -> pd.Series:
    """Boolean mask (index = stock id) of names allowed into the ranking:
    minimum price, minimum liquidity, minimum trading history, and (if
    enabled) a plain trend filter close > MA_fast > MA_slow so "strength"
    means a real uptrend rather than a one-day spike.
    """
    last_price = prices.iloc[-1]
    eligible = last_price >= cfg.min_price

    history_len = prices.notna().sum()
    eligible &= history_len >= cfg.min_history_days

    avg_turnover = turnover.tail(20).mean()
    eligible &= avg_turnover >= cfg.min_avg_turnover_ntd

    if cfg.trend_filter and len(prices) >= cfg.ma_slow:
        ma_fast = prices.tail(cfg.ma_fast).mean()
        ma_slow = prices.tail(cfg.ma_slow).mean()
        eligible &= (last_price > ma_fast) & (ma_fast > ma_slow)

    return eligible.fillna(False)


def is_market_downtrend(benchmark: pd.Series, cfg: StrategyConfig) -> bool:
    if not cfg.use_market_regime_filter or len(benchmark) < cfg.benchmark_ma:
        return False
    ma = benchmark.tail(cfg.benchmark_ma).mean()
    return bool(benchmark.iloc[-1] < ma)


def select_portfolio(
    prices: pd.DataFrame,
    turnover: pd.DataFrame,
    benchmark: pd.Series,
    cfg: StrategyConfig,
    current_holdings: list[str] | None = None,
) -> tuple[list[str], pd.Series, int]:
    """Return (new_holdings, full_score_series, n_slots) using data up to and
    including the last row of `prices`/`turnover`/`benchmark` (no lookahead).

    Hysteresis rule: a name already held stays in the portfolio as long as
    it is still eligible and ranks better than `hold_buffer_rank`; this
    avoids swapping a name out and back in on marginal rank noise and cuts
    turnover/transaction costs. New entrants must rank in the top `n_slots`.

    `n_slots` shrinks to `cfg.defensive_top_n` when the benchmark is below
    its long moving average (regime filter), so the backtester can size
    position weights (1 / n_slots) consistently with the selection made here.
    """
    current_holdings = current_holdings or []
    scores = compute_momentum_scores(prices, cfg)
    eligible = apply_eligibility_filters(prices, turnover, cfg)

    ranked = scores[eligible.reindex(scores.index, fill_value=False)].sort_values(ascending=False)
    rank_of = {sid: i + 1 for i, sid in enumerate(ranked.index)}

    n_slots = cfg.defensive_top_n if is_market_downtrend(benchmark, cfg) else cfg.top_n

    kept = [
        sid for sid in current_holdings
        if rank_of.get(sid, np.inf) <= cfg.hold_buffer_rank
    ]
    kept = kept[:n_slots]

    new_holdings = list(kept)
    for sid in ranked.index:
        if len(new_holdings) >= n_slots:
            break
        if sid not in new_holdings:
            new_holdings.append(sid)

    return new_holdings, scores, n_slots
