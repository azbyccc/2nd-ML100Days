"""Pluggable market-data interface.

The strategy/backtester only depends on the `DataSource` interface below, so
you can swap in whichever way you have of getting Taiwan stock data without
touching the strategy logic.

Implementations provided:

- `SyntheticDataSource`  : reproducible fake data, no network needed. Used by
                           `run_demo.py` so the whole pipeline can be verified
                           end-to-end in an offline/sandboxed environment.
- `FinMindDataSource`    : real data via the free FinMind API
                           (https://finmindtrade.com/). Needs outbound network
                           access; a free API token raises the rate limit.
- `YahooFinanceDataSource`: real data via `yfinance` (ticker.TW / ticker.TWO).
                           Needs outbound network access and `pip install yfinance`.
- `CSVDataSource`        : load prices you already downloaded/exported yourself.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from datetime import date, datetime

import numpy as np
import pandas as pd


class DataSource(ABC):
    """Minimal interface the strategy/backtester rely on."""

    @abstractmethod
    def get_universe(self) -> list[str]:
        """Return the list of stock ids to consider."""

    @abstractmethod
    def get_prices(self, stock_ids: list[str], start: str, end: str) -> pd.DataFrame:
        """Adjusted close price. Index = trading dates, columns = stock ids."""

    @abstractmethod
    def get_turnover(self, stock_ids: list[str], start: str, end: str) -> pd.DataFrame:
        """Daily traded value in NTD (close * volume is fine). Same shape as get_prices."""

    def get_benchmark(self, start: str, end: str) -> pd.Series:
        """Optional: a market index series (e.g. TAIEX / 0050) for the regime filter
        and for performance comparison. Default: equal-weight average of the universe.
        """
        prices = self.get_prices(self.get_universe(), start, end)
        return prices.mean(axis=1).rename("benchmark")


# --------------------------------------------------------------------------- #
# Synthetic data source (offline demo / unit tests)
# --------------------------------------------------------------------------- #
class SyntheticDataSource(DataSource):
    """Generates a reproducible fake universe of "stocks" with a mix of trend
    regimes (steady uptrend / downtrend / choppy / momentum-then-reversal) so
    that a momentum ranking has real signal to pick up on. This lets the whole
    pipeline (scoring -> filtering -> selection -> weekly backtest -> metrics)
    be exercised without any network access.
    """

    def __init__(self, n_stocks: int = 120, seed: int = 42):
        self.n_stocks = n_stocks
        self.seed = seed
        self._prices: pd.DataFrame | None = None
        self._turnover: pd.DataFrame | None = None

    def _build(self):
        if self._prices is not None:
            return
        rng = np.random.default_rng(self.seed)
        dates = pd.bdate_range("2021-01-04", "2024-12-31")
        n = len(dates)

        # Shared market factor so stocks are correlated and the benchmark has
        # realistic index-like volatility (an equal-weight average of fully
        # independent random walks would diversify away almost all vol, which
        # is not representative of a real market).
        market_shocks = rng.normal(loc=0.00035, scale=0.011, size=n)  # ~9%/yr drift, ~17%/yr vol
        self._market_shocks = market_shocks

        stock_ids = [f"S{1000 + i}" for i in range(self.n_stocks)]
        prices = pd.DataFrame(index=dates, columns=stock_ids, dtype=float)
        turnover = pd.DataFrame(index=dates, columns=stock_ids, dtype=float)

        regimes = ["strong_trend", "weak_trend", "choppy", "trend_reversal", "downtrend"]
        regime_probs = [0.2, 0.25, 0.25, 0.15, 0.15]

        for i, sid in enumerate(stock_ids):
            regime = rng.choice(regimes, p=regime_probs)
            p0 = rng.uniform(15, 300)
            beta = rng.uniform(0.6, 1.4)
            idio_vol = rng.uniform(0.008, 0.02)

            if regime == "strong_trend":
                alpha = rng.uniform(0.0008, 0.0016)
            elif regime == "weak_trend":
                alpha = rng.uniform(0.0001, 0.0005)
            elif regime == "choppy":
                alpha = rng.uniform(-0.0002, 0.0002)
            elif regime == "downtrend":
                alpha = rng.uniform(-0.0016, -0.0006)
            else:  # trend_reversal: strong for first ~50-70%, then reverses
                alpha = rng.uniform(0.0008, 0.0016)

            idio_shocks = rng.normal(loc=alpha, scale=idio_vol, size=n)
            if regime == "trend_reversal":
                flip = int(n * rng.uniform(0.5, 0.7))
                idio_shocks[flip:] = rng.normal(loc=-abs(alpha) * 1.5, scale=idio_vol, size=n - flip)

            stock_shocks = beta * market_shocks + idio_shocks
            log_prices = np.log(p0) + np.cumsum(stock_shocks)
            series = np.exp(log_prices)

            # simulate a later IPO for a handful of names (tests min_history_days)
            if rng.random() < 0.08:
                cutoff = rng.integers(20, 100)
                series[:cutoff] = np.nan

            prices[sid] = series

            base_vol = rng.uniform(2e5, 5e6)  # shares/day baseline
            vol_noise = rng.lognormal(mean=0, sigma=0.5, size=n)
            turnover[sid] = series * base_vol * vol_noise

        self._prices = prices
        self._turnover = turnover
        self._dates = dates

    def get_universe(self) -> list[str]:
        self._build()
        return list(self._prices.columns)

    def get_prices(self, stock_ids: list[str], start: str, end: str) -> pd.DataFrame:
        self._build()
        df = self._prices.loc[start:end, stock_ids]
        return df

    def get_turnover(self, stock_ids: list[str], start: str, end: str) -> pd.DataFrame:
        self._build()
        return self._turnover.loc[start:end, stock_ids]

    def get_benchmark(self, start: str, end: str) -> pd.Series:
        self._build()
        # the shared market factor itself, i.e. a TAIEX-like broad index,
        # rather than an average of the (much noisier) individual names
        index = 100.0 * np.exp(np.cumsum(self._market_shocks))
        return pd.Series(index, index=self._dates, name="benchmark").loc[start:end]


# --------------------------------------------------------------------------- #
# FinMind (https://finmindtrade.com) - free Taiwan market data API
# --------------------------------------------------------------------------- #
class FinMindDataSource(DataSource):
    """Fetches real TWSE/OTC daily prices from the FinMind API.

    Requires outbound network access to `api.finmindtrade.com` (blocked in
    some sandboxed environments). Get a free token at finmindtrade.com to
    raise the anonymous rate limit.
    """

    BASE_URL = "https://api.finmindtrade.com/api/v4/data"

    def __init__(self, stock_ids: list[str], token: str | None = None):
        self._stock_ids = stock_ids
        self.token = token or os.environ.get("FINMIND_TOKEN")

    def get_universe(self) -> list[str]:
        return list(self._stock_ids)

    def _fetch_one(self, dataset: str, stock_id: str, start: str, end: str) -> pd.DataFrame:
        import requests

        params = {
            "dataset": dataset,
            "data_id": stock_id,
            "start_date": start,
            "end_date": end,
        }
        if self.token:
            params["token"] = self.token
        resp = requests.get(self.BASE_URL, params=params, timeout=30)
        resp.raise_for_status()
        payload = resp.json()
        return pd.DataFrame(payload.get("data", []))

    def get_prices(self, stock_ids: list[str], start: str, end: str) -> pd.DataFrame:
        cols = {}
        for sid in stock_ids:
            df = self._fetch_one("TaiwanStockPrice", sid, start, end)
            if df.empty:
                continue
            df["date"] = pd.to_datetime(df["date"])
            cols[sid] = df.set_index("date")["close"]
        return pd.DataFrame(cols).sort_index()

    def get_turnover(self, stock_ids: list[str], start: str, end: str) -> pd.DataFrame:
        cols = {}
        for sid in stock_ids:
            df = self._fetch_one("TaiwanStockPrice", sid, start, end)
            if df.empty:
                continue
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date")
            cols[sid] = df["close"] * df["Trading_Volume"]
        return pd.DataFrame(cols).sort_index()

    def get_benchmark(self, start: str, end: str) -> pd.Series:
        df = self._fetch_one("TaiwanStockPrice", "TAIEX", start, end)
        df["date"] = pd.to_datetime(df["date"])
        return df.set_index("date")["close"].rename("benchmark")


# --------------------------------------------------------------------------- #
# Yahoo Finance via yfinance (2330.TW / 6547.TWO style tickers)
# --------------------------------------------------------------------------- #
class YahooFinanceDataSource(DataSource):
    """Requires `pip install yfinance` and outbound network access to
    query1.finance.yahoo.com. `stock_ids` should already carry the .TW /
    .TWO suffix, e.g. ["2330.TW", "2317.TW", "6547.TWO"].
    """

    def __init__(self, stock_ids: list[str], benchmark: str = "^TWII"):
        self._stock_ids = stock_ids
        self._benchmark = benchmark

    def get_universe(self) -> list[str]:
        return list(self._stock_ids)

    def _download(self, tickers: list[str], start: str, end: str) -> pd.DataFrame:
        import yfinance as yf

        data = yf.download(tickers, start=start, end=end, auto_adjust=True, progress=False)
        return data

    def get_prices(self, stock_ids: list[str], start: str, end: str) -> pd.DataFrame:
        data = self._download(stock_ids, start, end)
        close = data["Close"] if isinstance(data.columns, pd.MultiIndex) else data[["Close"]]
        if isinstance(close, pd.Series):
            close = close.to_frame(stock_ids[0])
        return close

    def get_turnover(self, stock_ids: list[str], start: str, end: str) -> pd.DataFrame:
        data = self._download(stock_ids, start, end)
        close = data["Close"] if isinstance(data.columns, pd.MultiIndex) else data[["Close"]]
        vol = data["Volume"] if isinstance(data.columns, pd.MultiIndex) else data[["Volume"]]
        return close * vol

    def get_benchmark(self, start: str, end: str) -> pd.Series:
        data = self._download([self._benchmark], start, end)
        close = data["Close"] if isinstance(data.columns, pd.MultiIndex) else data["Close"]
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
        return close.rename("benchmark")


# --------------------------------------------------------------------------- #
# Local CSV files you already have
# --------------------------------------------------------------------------- #
class CSVDataSource(DataSource):
    """Expects one CSV per stock in `directory`, named `<stock_id>.csv`, with
    at least columns: date, close, volume.
    """

    def __init__(self, directory: str, stock_ids: list[str] | None = None):
        self.directory = directory
        self._stock_ids = stock_ids or [
            f[:-4] for f in os.listdir(directory) if f.endswith(".csv")
        ]

    def get_universe(self) -> list[str]:
        return list(self._stock_ids)

    def _load(self, stock_id: str) -> pd.DataFrame:
        path = os.path.join(self.directory, f"{stock_id}.csv")
        df = pd.read_csv(path, parse_dates=["date"]).set_index("date").sort_index()
        return df

    def get_prices(self, stock_ids: list[str], start: str, end: str) -> pd.DataFrame:
        cols = {sid: self._load(sid)["close"] for sid in stock_ids}
        return pd.DataFrame(cols).loc[start:end]

    def get_turnover(self, stock_ids: list[str], start: str, end: str) -> pd.DataFrame:
        cols = {}
        for sid in stock_ids:
            df = self._load(sid)
            cols[sid] = df["close"] * df["volume"]
        return pd.DataFrame(cols).loc[start:end]
