"""Order block strategy."""

from __future__ import annotations

from goldbot.execution.order_models import CandidateSignal, Signal
from goldbot.strategies.base import Strategy, hold


class OrderBlockStrategy(Strategy):
    name = "order_block"

    def evaluate(self, bars: list[dict]) -> CandidateSignal:
        if len(bars) < 8:
            return hold(self.name, "Not enough bars")
        last = bars[-1]
        atr = max(1e-6, float(last["atr"]))
        price = float(last["close"])

        for i in range(len(bars) - 5, 1, -1):
            block = bars[i]
            if float(block["close"]) < float(block["open"]):
                move = bars[i + 1 : i + 4]
                if len(move) < 3:
                    continue
                strong = all(float(c["close"]) > float(c["open"]) for c in move)
                thrust = float(move[-1]["close"]) - float(block["close"])
                if not strong and thrust <= 2 * atr:
                    continue
                ob_low = float(block["low"])
                ob_high = float(block["high"])
                was_tested = any(float(c["low"]) <= ob_high and float(c["high"]) >= ob_low for c in bars[i + 1 : -1])
                if was_tested:
                    continue
                if ob_low <= price <= ob_high:
                    sl_basis = max(0.1, price - (ob_low - 0.1 * atr))
                    return CandidateSignal(
                        self.name,
                        Signal.BUY,
                        0.75 if strong else 0.65,
                        "Return to fresh demand order block",
                        sl_basis,
                        max(0.1, sl_basis * 2.0),
                    )

            if float(block["close"]) > float(block["open"]):
                move = bars[i + 1 : i + 4]
                if len(move) < 3:
                    continue
                strong = all(float(c["close"]) < float(c["open"]) for c in move)
                thrust = float(block["close"]) - float(move[-1]["close"])
                if not strong and thrust <= 2 * atr:
                    continue
                ob_low = float(block["low"])
                ob_high = float(block["high"])
                was_tested = any(float(c["low"]) <= ob_high and float(c["high"]) >= ob_low for c in bars[i + 1 : -1])
                if was_tested:
                    continue
                if ob_low <= price <= ob_high:
                    sl_basis = max(0.1, (ob_high + 0.1 * atr) - price)
                    return CandidateSignal(
                        self.name,
                        Signal.SELL,
                        0.75 if strong else 0.65,
                        "Return to fresh supply order block",
                        sl_basis,
                        max(0.1, sl_basis * 2.0),
                    )

        return hold(self.name, "No order block setup")
