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
        close = float(last["close"])
        bb_lower = float(last["bb_lower"])
        bb_upper = float(last["bb_upper"])
        rsi = float(last["rsi"])
        atr = float(last["atr"])

        if rsi <= 35 and close <= bb_lower + (0.2 * atr):
            return CandidateSignal(self.name, Signal.BUY, 0.65, "Oversold near lower band", atr * 1.0, atr * 1.6)
        if rsi >= 65 and close >= bb_upper - (0.2 * atr):
            return CandidateSignal(self.name, Signal.SELL, 0.65, "Overbought near upper band", atr * 1.0, atr * 1.6)
        return hold(self.name, "No mean-reversion setup")
