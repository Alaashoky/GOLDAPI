"""London/NY breakout strategy."""

from __future__ import annotations

from goldbot.execution.order_models import CandidateSignal, Signal
from goldbot.strategies.base import Strategy, hold


class BreakoutLondonNYStrategy(Strategy):
    name = "breakout_london_ny"

    def __init__(self, lookback: int = 24) -> None:
        self.lookback = lookback

    def evaluate(self, bars: list[dict]) -> CandidateSignal:
        if len(bars) < self.lookback + 1:
            return hold(self.name, "Not enough bars")
        window = bars[-(self.lookback + 1) : -1]
        last = bars[-1]
        high = max(float(b["high"]) for b in window)
        low = min(float(b["low"]) for b in window)
        rng = max(1e-6, high - low)

        if last["close"] > high:
            return CandidateSignal(self.name, Signal.BUY, min(1.0, (last["close"] - high) / rng + 0.4), "Breakout above session range", last["atr"] * 1.3, last["atr"] * 2.2)
        if last["close"] < low:
            return CandidateSignal(self.name, Signal.SELL, min(1.0, (low - last["close"]) / rng + 0.4), "Breakout below session range", last["atr"] * 1.3, last["atr"] * 2.2)
        return hold(self.name, "No breakout")
