"""Simple backtest engine."""

from __future__ import annotations

from goldbot.backtest.metrics import calculate_metrics
from goldbot.execution.order_models import Signal
from goldbot.risk.position_sizing import calculate_position_size
from goldbot.strategies.base import Strategy


class BacktestEngine:
    WARMUP_BARS = 30

    def _apply_h1_trend_filter(self, signal: Signal, strategy: Strategy, h1_trend: str | None) -> bool:
        if strategy.name != "liquidity_sweep":
            return True
        trend = (h1_trend or "").lower()
        if signal == Signal.BUY:
            return trend == "bullish"
        if signal == Signal.SELL:
            return trend == "bearish"
        return True

    def _pnl(self, side: str, entry: float, exit_price: float, lot: float, contract_size: float) -> float:
        if side == Signal.BUY.value:
            return (exit_price - entry) * lot * contract_size
        return (entry - exit_price) * lot * contract_size

    def run(
        self,
        bars: list[dict],
        strategy: Strategy,
        starting_balance: float = 10000.0,
        risk_per_trade_pct: float = 0.5,
        entry_model: str = "next_open",
        spread_points: float = 0.0,
        point_value: float = 0.0,
        contract_size: float = 100.0,
        volume_min: float = 0.01,
        volume_step: float = 0.01,
        volume_max: float = 100.0,
        h1_trends: list[str] | None = None,
    ) -> dict:
        balance = starting_balance
        equity_curve = [balance]
        trades: list[dict] = []
        position = None
        pending_entry = None
        spread_price = spread_points * point_value

        for i in range(self.WARMUP_BARS, len(bars)):
            sample = bars[: i + 1]
            current = bars[i]

            if pending_entry and position is None:
                raw_open = float(current["open"])
                entry = raw_open + spread_price if pending_entry["signal"] == Signal.BUY.value else raw_open - spread_price
                sl_distance = float(pending_entry["sl_distance"])
                tp_distance = sl_distance * 2.0
                if pending_entry["signal"] == Signal.BUY.value:
                    sl = entry - sl_distance
                    tp = entry + tp_distance
                else:
                    sl = entry + sl_distance
                    tp = entry - tp_distance
                lot = calculate_position_size(
                    account_balance=balance,
                    risk_per_trade_pct=risk_per_trade_pct,
                    entry_price=entry,
                    sl_price=sl,
                    contract_size=contract_size,
                    volume_min=volume_min,
                    volume_step=volume_step,
                    volume_max=volume_max,
                )
                if lot > 0:
                    position = {
                        "side": pending_entry["signal"],
                        "entry": entry,
                        "sl": sl,
                        "tp": tp,
                        "lot": lot,
                        "entry_index": i,
                        "signal_index": pending_entry["signal_index"],
                    }
                pending_entry = None

            if position:
                side = position["side"]
                sl_hit = float(current["low"]) <= position["sl"] if side == Signal.BUY.value else float(current["high"]) >= position["sl"]
                tp_hit = float(current["high"]) >= position["tp"] if side == Signal.BUY.value else float(current["low"]) <= position["tp"]
                if sl_hit or tp_hit:
                    # If both SL and TP are touched in the same candle, SL takes precedence.
                    exit_price = position["sl"] if sl_hit else position["tp"]
                    outcome = "SL" if sl_hit else "TP"
                    pnl = self._pnl(side, position["entry"], exit_price, position["lot"], contract_size)
                    risk_amount = abs(position["entry"] - position["sl"]) * position["lot"] * contract_size
                    r_multiple = (pnl / risk_amount) if risk_amount > 0 else 0.0
                    balance += pnl
                    trades.append(
                        {
                            "signal": side,
                            "entry": position["entry"],
                            "sl": position["sl"],
                            "tp": position["tp"],
                            "exit": exit_price,
                            "lot": position["lot"],
                            "pnl": pnl,
                            "reason": outcome,
                            "r": r_multiple,
                            "entry_index": position["entry_index"],
                            "exit_index": i,
                            "signal_index": position["signal_index"],
                            "entry_time": bars[position["entry_index"]].get("time"),
                            "exit_time": current.get("time"),
                        }
                    )
                    position = None

            if position is None:
                decision = strategy.evaluate(sample)
                if decision.signal in {Signal.BUY, Signal.SELL}:
                    h1_trend = h1_trends[i] if h1_trends is not None and i < len(h1_trends) else None
                    if not self._apply_h1_trend_filter(decision.signal, strategy, h1_trend):
                        equity_curve.append(balance)
                        continue
                    if entry_model == "next_open":
                        if i + 1 < len(bars):
                            pending_entry = {
                                "signal": decision.signal.value,
                                "sl_distance": decision.sl_basis,
                                "signal_index": i,
                            }
                    else:
                        entry = float(current["close"])
                        entry += spread_price if decision.signal == Signal.BUY else -spread_price
                        tp_distance = float(decision.sl_basis) * 2.0
                        if decision.signal == Signal.BUY:
                            sl = entry - decision.sl_basis
                            tp = entry + tp_distance
                        else:
                            sl = entry + decision.sl_basis
                            tp = entry - tp_distance
                        lot = calculate_position_size(
                            account_balance=balance,
                            risk_per_trade_pct=risk_per_trade_pct,
                            entry_price=entry,
                            sl_price=sl,
                            contract_size=contract_size,
                            volume_min=volume_min,
                            volume_step=volume_step,
                            volume_max=volume_max,
                        )
                        if lot > 0:
                            position = {
                                "side": decision.signal.value,
                                "entry": entry,
                                "sl": sl,
                                "tp": tp,
                                "lot": lot,
                                "entry_index": i,
                                "signal_index": i,
                            }
            equity_curve.append(balance)

        return {
            "starting_balance": starting_balance,
            "ending_balance": balance,
            "total_pnl": balance - starting_balance,
            "metrics": calculate_metrics(trades, equity_curve),
            "trades": trades,
        }
