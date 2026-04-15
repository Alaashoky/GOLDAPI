"""ATR volatility expansion strategy."""

from __future__ import annotations

from goldbot.execution.order_models import CandidateSignal, Signal
from goldbot.strategies.base import Strategy, hold


class ATRVolExpansionStrategy(Strategy):
    name = "atr_vol_expansion"

    def __init__(self, mult: float = 1.2) -> None:
        self.mult = mult

    def evaluate(self, bars: list[dict]) -> CandidateSignal:
        if len(bars) < 2:
            return hold(self.name, "Not enough bars")
        last = bars[-1]
        bar_range = float(last["high"]) - float(last["low"])
        if bar_range < float(last["atr"]) * self.mult:
            return hold(self.name, "No ATR expansion")
        if last["close"] > last["open"]:
            return CandidateSignal(self.name, Signal.BUY, 0.6, "Bullish volatility expansion", last["atr"] * 1.2, last["atr"] * 2.0)
        if last["close"] < last["open"]:
            return CandidateSignal(self.name, Signal.SELL, 0.6, "Bearish volatility expansion", last["atr"] * 1.2, last["atr"] * 2.0)
        return hold(self.name, "Neutral expansion")
