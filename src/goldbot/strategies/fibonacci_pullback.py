"""Fibonacci retracement pullback strategy."""

from __future__ import annotations

from goldbot.execution.order_models import CandidateSignal, Signal
from goldbot.strategies.base import Strategy, hold


class FibonacciPullbackStrategy(Strategy):
    name = "fibonacci_pullback"

    def __init__(self, lookback: int = 80) -> None:
        self.lookback = lookback

    def evaluate(self, bars: list[dict]) -> CandidateSignal:
        if len(bars) < self.lookback:
            return hold(self.name, "Not enough bars")
        window = bars[-self.lookback :]
        last = window[-1]
        swing_high = max(float(b["high"]) for b in window)
        swing_low = min(float(b["low"]) for b in window)
        move = swing_high - swing_low
        if move <= 0:
            return hold(self.name, "Invalid swing range")

        trend_up = float(last["ema_fast"]) > float(last["ema_slow"])
        trend_down = float(last["ema_fast"]) < float(last["ema_slow"])
        price = float(last["close"])
        rsi = float(last["rsi"])
        if not (30 <= rsi <= 70):
            return hold(self.name, "RSI extreme")

        if trend_up:
            level_382 = swing_high - (move * 0.382)
            level_500 = swing_high - (move * 0.5)
            level_618 = swing_high - (move * 0.618)
            level_786 = swing_high - (move * 0.786)
            if level_618 <= price <= level_382:
                confidence = 0.85 if price <= level_500 else 0.75
                return CandidateSignal(
                    self.name,
                    Signal.BUY,
                    confidence,
                    "Price at Fibonacci pullback zone in uptrend",
                    max(0.1, price - level_786),
                    max(0.1, swing_high - price),
                )

        if trend_down:
            level_382 = swing_low + (move * 0.382)
            level_500 = swing_low + (move * 0.5)
            level_618 = swing_low + (move * 0.618)
            level_786 = swing_low + (move * 0.786)
            if level_382 <= price <= level_618:
                confidence = 0.85 if price >= level_500 else 0.75
                return CandidateSignal(
                    self.name,
                    Signal.SELL,
                    confidence,
                    "Price at Fibonacci pullback zone in downtrend",
                    max(0.1, level_786 - price),
                    max(0.1, price - swing_low),
                )

        return hold(self.name, "No Fibonacci pullback setup")
