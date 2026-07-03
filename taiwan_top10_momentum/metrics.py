"""Performance metrics for a daily return series."""

from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def summarize(daily_returns: pd.Series, weekly_turnover: list[float] | None = None) -> dict:
    r = daily_returns.dropna()
    if r.empty:
        return {}

    equity = (1.0 + r).cumprod()
    n_years = len(r) / TRADING_DAYS

    total_return = equity.iloc[-1] - 1.0
    cagr = equity.iloc[-1] ** (1 / n_years) - 1.0 if n_years > 0 else np.nan
    ann_vol = r.std() * np.sqrt(TRADING_DAYS)
    sharpe = (r.mean() * TRADING_DAYS) / ann_vol if ann_vol > 0 else np.nan

    running_max = equity.cummax()
    drawdown = equity / running_max - 1.0
    max_dd = drawdown.min()
    calmar = cagr / abs(max_dd) if max_dd < 0 else np.nan

    weekly_r = (1 + r).resample("W-FRI").prod() - 1
    win_rate = (weekly_r > 0).mean() if len(weekly_r) else np.nan

    out = {
        "total_return": total_return,
        "cagr": cagr,
        "annual_vol": ann_vol,
        "sharpe": sharpe,
        "max_drawdown": max_dd,
        "calmar": calmar,
        "weekly_win_rate": win_rate,
        "n_weeks": len(weekly_r),
    }
    if weekly_turnover:
        out["avg_weekly_turnover_cost_bps"] = float(np.mean(weekly_turnover)) * 10_000
    return out


def format_summary(summary: dict, label: str = "Strategy") -> str:
    if not summary:
        return f"{label}: no data"
    lines = [f"== {label} =="]
    lines.append(f"Total return       : {summary['total_return']:+.2%}")
    lines.append(f"CAGR               : {summary['cagr']:+.2%}")
    lines.append(f"Annualized vol     : {summary['annual_vol']:.2%}")
    lines.append(f"Sharpe (rf=0)      : {summary['sharpe']:.2f}")
    lines.append(f"Max drawdown       : {summary['max_drawdown']:.2%}")
    lines.append(f"Calmar ratio       : {summary['calmar']:.2f}")
    lines.append(f"Weekly win rate    : {summary['weekly_win_rate']:.1%} ({summary['n_weeks']} weeks)")
    if "avg_weekly_turnover_cost_bps" in summary:
        lines.append(f"Avg weekly cost    : {summary['avg_weekly_turnover_cost_bps']:.1f} bps")
    return "\n".join(lines)
