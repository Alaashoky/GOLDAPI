"""Mean reversion strategy using RSI + Bollinger Bands."""

from __future__ import annotations

from goldbot.execution.order_models import CandidateSignal, Signal
from goldbot.strategies.base import Strategy, hold


class MeanReversionRSIBBStrategy(Strategy):
    name = "mean_reversion_rsi_bb"

    def evaluate(self, bars: list[dict]) -> CandidateSignal:
        if len(bars) < 2:
            return hold(self.name, "Not enough bars")
        last = bars[-1]

        if last["close"] <= last["bb_lower"] and last["rsi"] <= 30:
            return CandidateSignal(self.name, Signal.BUY, 0.65, "Oversold at lower band", last["atr"] * 1.0, last["atr"] * 1.6)
        if last["close"] >= last["bb_upper"] and last["rsi"] >= 70:
            return CandidateSignal(self.name, Signal.SELL, 0.65, "Overbought at upper band", last["atr"] * 1.0, last["atr"] * 1.6)
        return hold(self.name, "No mean-reversion setup")
