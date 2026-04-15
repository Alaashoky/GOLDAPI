"""Backtest metric calculations."""

from __future__ import annotations

from math import sqrt
from statistics import mean, pstdev


def calculate_metrics(trades: list[dict], equity_curve: list[float]) -> dict[str, float]:
    if not trades:
        return {"trades": 0.0, "win_rate": 0.0, "expectancy": 0.0, "max_drawdown": 0.0, "sharpe": 0.0}

    pnl_values = [float(t["pnl"]) for t in trades]
    wins = [x for x in pnl_values if x > 0]
    losses = [x for x in pnl_values if x <= 0]

    peak = equity_curve[0] if equity_curve else 0.0
    max_dd = 0.0
    for x in equity_curve:
        peak = max(peak, x)
        max_dd = max(max_dd, peak - x)

    avg = mean(pnl_values)
    sd = pstdev(pnl_values) if len(pnl_values) > 1 else 0.0
    sharpe = (avg / sd) * sqrt(len(pnl_values)) if sd > 0 else 0.0

    return {
        "trades": float(len(trades)),
        "win_rate": len(wins) / len(trades),
        "expectancy": avg,
        "max_drawdown": max_dd,
        "sharpe": sharpe,
        "gross_profit": sum(wins),
        "gross_loss": abs(sum(losses)),
    }
