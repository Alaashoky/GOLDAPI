"""Simple backtest engine."""

from __future__ import annotations

from goldbot.backtest.metrics import calculate_metrics
from goldbot.execution.order_models import Signal
from goldbot.strategies.base import Strategy


class BacktestEngine:
    def run(self, bars: list[dict], strategy: Strategy, starting_balance: float = 10000.0) -> dict:
        balance = starting_balance
        equity_curve = [balance]
        trades: list[dict] = []
        position = None

        for i in range(30, len(bars)):
            sample = bars[: i + 1]
            current = bars[i]
            if position:
                if position["side"] == "BUY":
                    if current["low"] <= position["sl"]:
                        pnl = (position["sl"] - position["entry"]) * position["lot"] * 100
                        balance += pnl
                        trades.append({"pnl": pnl, "exit": position["sl"], "reason": "SL"})
                        position = None
                    elif current["high"] >= position["tp"]:
                        pnl = (position["tp"] - position["entry"]) * position["lot"] * 100
                        balance += pnl
                        trades.append({"pnl": pnl, "exit": position["tp"], "reason": "TP"})
                        position = None
                else:
                    if current["high"] >= position["sl"]:
                        pnl = (position["entry"] - position["sl"]) * position["lot"] * 100
                        balance += pnl
                        trades.append({"pnl": pnl, "exit": position["sl"], "reason": "SL"})
                        position = None
                    elif current["low"] <= position["tp"]:
                        pnl = (position["entry"] - position["tp"]) * position["lot"] * 100
                        balance += pnl
                        trades.append({"pnl": pnl, "exit": position["tp"], "reason": "TP"})
                        position = None

            if position is None:
                decision = strategy.evaluate(sample)
                if decision.signal in {Signal.BUY, Signal.SELL}:
                    entry = float(current["close"])
                    if decision.signal == Signal.BUY:
                        sl = entry - decision.sl_basis
                        tp = entry + decision.tp_basis
                    else:
                        sl = entry + decision.sl_basis
                        tp = entry - decision.tp_basis
                    position = {
                        "side": decision.signal.value,
                        "entry": entry,
                        "sl": sl,
                        "tp": tp,
                        "lot": 0.1,
                    }
            equity_curve.append(balance)

        return {"starting_balance": starting_balance, "ending_balance": balance, "metrics": calculate_metrics(trades, equity_curve), "trades": trades}
