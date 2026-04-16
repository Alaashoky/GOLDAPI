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

        price = float(last["close"])
        rsi = float(last["rsi"])
        ema_fast = float(last["ema_fast"])
        ema_slow = float(last["ema_slow"])
        if not (25 <= rsi <= 75):
            return hold(self.name, f"RSI extreme ({rsi:.1f})")

        ema_diff_pct = ((ema_fast - ema_slow) / max(1e-6, price)) * 100

        level_382_up = swing_high - (move * 0.382)
        level_500_up = swing_high - (move * 0.5)
        level_618_up = swing_high - (move * 0.618)
        level_786_up = swing_high - (move * 0.786)
        in_buy_zone = level_618_up <= price <= level_382_up
        can_buy = ema_diff_pct > -0.05
        if in_buy_zone and can_buy:
            confidence = 0.85 if price <= level_500_up else 0.7
            if ema_diff_pct < 0:
                confidence *= 0.8
            return CandidateSignal(
                self.name,
                Signal.BUY,
                confidence,
                f"Price at Fibonacci pullback zone ({price:.2f} in {level_618_up:.2f}-{level_382_up:.2f})",
                max(0.1, price - level_786_up),
                max(0.1, swing_high - price),
            )

        level_382_dn = swing_low + (move * 0.382)
        level_500_dn = swing_low + (move * 0.5)
        level_618_dn = swing_low + (move * 0.618)
        level_786_dn = swing_low + (move * 0.786)
        in_sell_zone = level_382_dn <= price <= level_618_dn
        can_sell = ema_diff_pct < 0.05
        if in_sell_zone and can_sell:
            confidence = 0.85 if price >= level_500_dn else 0.7
            if ema_diff_pct > 0:
                confidence *= 0.8
            return CandidateSignal(
                self.name,
                Signal.SELL,
                confidence,
                f"Price at Fibonacci retracement zone ({price:.2f} in {level_382_dn:.2f}-{level_618_dn:.2f})",
                max(0.1, level_786_dn - price),
                max(0.1, price - swing_low),
            )

        return hold(
            self.name,
            (
                f"Price {price:.2f} not in fib zone "
                f"(buy: {level_618_up:.2f}-{level_382_up:.2f}, sell: {level_382_dn:.2f}-{level_618_dn:.2f})"
            ),
        )
