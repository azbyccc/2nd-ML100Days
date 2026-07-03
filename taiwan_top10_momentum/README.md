# 台股強勢10檔動能策略（每週換倉）

A weekly-rebalanced Taiwan-equity momentum strategy: rank the investable
universe by a composite "strength" score, hold the top 10, roll the book
every week. This folder is a runnable reference implementation, not just a
write-up.

> **Not investment advice.** This is an educational backtest framework.
> Past/simulated performance does not predict future returns.

## Strategy design

**Universe** — all TWSE/OTC common stocks, excluding ETFs/warrants, subject
to eligibility filters below.

**Strength score** — composite momentum, computed cross-sectionally each
week:

```
score = 0.4 * pct_rank(20-day return)   # ~4 weeks
      + 0.3 * pct_rank(60-day return)   # ~12 weeks
      + 0.3 * pct_rank(120-day return)  # ~24 weeks
```

Returns are converted to a 0–1 percentile rank *before* being averaged
(instead of averaging raw returns), so no single blow-up name dominates and
every lookback window contributes on the same scale. Weights favor recent
(4-week) momentum but blend in medium-term trend so the strategy doesn't
chase one-week noise. Tune windows/weights in `config.py`.

**Eligibility filters** (a stock must pass all of these to enter the
ranking) — this is what keeps "strong" from meaning "one wild spike":

- Price ≥ NT$10 (avoid penny/whipsaw names near delisting thresholds)
- 20-day average traded value ≥ NT$20M (avoid illiquid names you can't
  actually fill 10%+ of the book in without moving the price)
- ≥130 trading days of history (excludes very recent IPOs before their
  price-discovery period settles)
- Trend filter: `close > MA20 > MA60` (moving averages stacked in the
  right order) — the stock must be in an actual uptrend, not just posting a
  high raw return off a crash.

**Selection with hysteresis** — pick the top 10 by score among eligible
names. A name already held stays in the book as long as it's still eligible
and hasn't fallen past rank 15 (`hold_buffer_rank`), rather than being sold
the moment a competitor edges ahead by a hair. This materially cuts
week-to-week turnover/costs without changing the strategy's character.

**Regime filter (risk-off switch)** — if the benchmark (TAIEX/0050 proxy)
is below its 120-day moving average, the book shrinks from 10 to 5 names
(`defensive_top_n`). In a broad downtrend there are usually few genuine
"strong" stocks left, and this reduces exposure/whipsaw instead of forcing
a full 10-name book out of a shrinking eligible set.

**Weighting** — equal weight across the active slots (10 normally, 5 in
defensive regime). Unfilled slots (not enough eligible names) sit in cash
rather than being force-allocated.

**Rebalance cadence** — signal computed off Friday's close (or the last
trading day of the week); executed at the next trading day's open (Monday).
No lookahead: every score/filter/regime computation only uses data through
the signal date.

**Transaction costs** (Taiwan-specific, in `config.py`):
- Buy: 0.1425% brokerage fee
- Sell: 0.1425% brokerage fee + 0.3% securities transaction tax
- Applied to the one-way turnover at each rebalance (only the names that
  actually change weight), charged as a one-time drag on the execution
  day's return.

## Files

| File | Purpose |
|---|---|
| `config.py` | All tunable parameters (`StrategyConfig`) |
| `data_source.py` | Pluggable data interface + Synthetic/FinMind/Yahoo/CSV implementations |
| `strategy.py` | Scoring, eligibility filters, regime filter, top-N selection with hysteresis |
| `backtest.py` | Weekly-rebalance event loop, no-lookahead, transaction costs |
| `metrics.py` | CAGR, Sharpe, max drawdown, Calmar, weekly win rate |
| `run_demo.py` | Runs the full pipeline end-to-end and prints/plots results |

## Running the demo

```bash
pip install -r requirements.txt
python run_demo.py
```

This uses `SyntheticDataSource` — a reproducible fake universe of 120
tickers with a shared market factor (so the benchmark has realistic index
volatility/correlation) plus a mix of trend/downtrend/choppy/reversal
regimes per name, so the momentum ranking has real signal to find. It's
there so the whole pipeline (scoring → filtering → selection → weekly
backtest → metrics) can be verified without any network access — this
sandbox's outbound network policy blocks Yahoo Finance / FinMind, so real
data can't be fetched from here. Output goes to `output/`:
`equity_curve.png` and `holdings_history.csv`.

## Switching to real Taiwan market data

Nothing in `strategy.py` / `backtest.py` needs to change — only swap the
data source in `run_demo.py` (or your own script):

**Option A — FinMind (free, no extra dependency beyond `requests`)**
```python
from data_source import FinMindDataSource

stock_ids = ["2330", "2317", "2454", ...]   # TWSE stock codes, no suffix
source = FinMindDataSource(stock_ids, token="YOUR_FINMIND_TOKEN")  # token optional but raises rate limit
```
Get a free token at https://finmindtrade.com/.

**Option B — Yahoo Finance via `yfinance`**
```python
pip install yfinance

from data_source import YahooFinanceDataSource
stock_ids = ["2330.TW", "2317.TW", "6547.TWO", ...]  # .TW = TWSE, .TWO = OTC
source = YahooFinanceDataSource(stock_ids, benchmark="^TWII")
```

**Option C — your own CSV exports**
```python
from data_source import CSVDataSource
source = CSVDataSource("path/to/csv_dir")  # one <stock_id>.csv per stock, columns: date, close, volume
```

For a full-market universe (rather than a hand-picked list), pull the
constituent list of an index like 0050/0051 or the whole TWSE listing from
TWSE OpenAPI / FinMind's `TaiwanStockInfo` dataset and pass those stock ids
to whichever data source you pick.

## Known limitations

- No slippage/market-impact model beyond the fee schedule — fine for
  liquid names, understates cost for large orders in thin names.
- No short side / leverage; long-only, cash-or-invested.
- The regime filter uses a single benchmark MA crossover — a blunt
  instrument. Consider blending in breadth (e.g. % of universe above its
  own MA200) for a less binary signal.
- Backtest assumes fills at each stock's own close-to-close return during
  the holding period, i.e. no intra-day execution price differences from
  the actual Monday open print.
