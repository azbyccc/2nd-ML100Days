"""Tunable parameters for the Taiwan Top-10 Momentum strategy."""

from dataclasses import dataclass, field


@dataclass
class StrategyConfig:
    # --- Portfolio construction ---
    top_n: int = 10                       # number of holdings
    hold_buffer_rank: int = 15            # hysteresis: keep an existing holding
                                           # until its rank falls below this,
                                           # instead of churning every week
    max_weight_per_stock: float = 0.15    # cap on a single name's weight

    # --- Composite momentum score ---
    # lookback windows in *trading days* (~5 trading days per week)
    lookback_days: dict = field(default_factory=lambda: {"w4": 20, "w12": 60, "w24": 120})
    lookback_weights: dict = field(default_factory=lambda: {"w4": 0.4, "w12": 0.3, "w24": 0.3})

    # --- Trend / eligibility filters ("strength" must be a real uptrend) ---
    trend_filter: bool = True
    ma_fast: int = 20                     # close > MA20 > MA60 required
    ma_slow: int = 60
    min_price: float = 10.0               # avoid cash-out/penny stocks
    min_avg_turnover_ntd: float = 20_000_000  # 20-day avg traded value (NTD)
    min_history_days: int = 130           # exclude very recent IPOs

    # --- Regime filter (risk-off switch) ---
    use_market_regime_filter: bool = True
    benchmark_ma: int = 120               # if benchmark < its 120d MA, cut exposure
    defensive_top_n: int = 5              # hold fewer names in a downtrend regime

    # --- Rebalance cadence ---
    rebalance_weekday: int = 4            # Monday=0 ... Friday=4; signal computed
                                           # on this weekday's close, executed next
                                           # trading day's open

    # --- Taiwan transaction cost model ---
    buy_fee_bps: float = 14.25            # 0.1425% brokerage fee (buy)
    sell_fee_bps: float = 14.25           # 0.1425% brokerage fee (sell)
    sell_tax_bps: float = 30.0            # 0.3% securities transaction tax (sell only)
