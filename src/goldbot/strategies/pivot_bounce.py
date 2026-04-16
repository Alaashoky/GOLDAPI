"""Pivot point bounce strategy."""

from __future__ import annotations

from statistics import mean

from goldbot.execution.order_models import CandidateSignal, Signal
from goldbot.strategies.base import Strategy, hold


class PivotBounceStrategy(Strategy):
    name = "pivot_bounce"

    def evaluate(self, bars: list[dict]) -> CandidateSignal:
        if len(bars) < 10:
            return hold(self.name, "Not enough bars")
        last = bars[-1]
        prev = bars[-2]
        atr = max(1e-6, float(last["atr"]))
        avg_atr = mean(float(b.get("atr", atr)) for b in bars[-10:])
        if atr > 2 * max(1e-6, avg_atr):
            return hold(self.name, "ATR too high for pivot bounce")

        close = float(last["close"])
        prev_close = float(prev["close"])
        pivot = float(last["pivot"])
        s1 = float(last["pivot_s1"])
        r1 = float(last["pivot_r1"])
        level_zone = 0.3 * atr
        trend_up = float(last["ema_fast"]) >= float(last["ema_slow"])
        trend_down = float(last["ema_fast"]) <= float(last["ema_slow"])

        if prev_close <= s1 + level_zone and close > s1 and close > prev_close:
            confidence = 0.75 if trend_up else 0.6
            return CandidateSignal(
                self.name,
                Signal.BUY,
                confidence,
                "Bounce up from pivot support",
                max(0.1, close - (s1 - 0.5 * atr)),
                max(0.1, pivot - close),
            )
        if prev_close >= r1 - level_zone and close < r1 and close < prev_close:
            confidence = 0.75 if trend_down else 0.6
            return CandidateSignal(
                self.name,
                Signal.SELL,
                confidence,
                "Bounce down from pivot resistance",
                max(0.1, (r1 + 0.5 * atr) - close),
                max(0.1, close - pivot),
            )
        return hold(self.name, "No pivot bounce setup")
