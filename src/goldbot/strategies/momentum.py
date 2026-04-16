"""Simple momentum strategy — fires on strong directional moves."""

from __future__ import annotations

from goldbot.execution.order_models import CandidateSignal, Signal
from goldbot.strategies.base import Strategy, hold


class MomentumStrategy(Strategy):
    name = "momentum"

    def evaluate(self, bars: list[dict]) -> CandidateSignal:
        if len(bars) < 5:
            return hold(self.name, "Not enough bars")

        last = bars[-1]
        prev = bars[-2]
        prev2 = bars[-3]

        close = float(last["close"])
        prev_close = float(prev["close"])
        prev2_close = float(prev2["close"])
        atr = max(1e-6, float(last["atr"]))
        rsi = float(last["rsi"])
        macd_hist = float(last.get("macd_hist", 0))
        ema_fast = float(last["ema_fast"])
        ema_slow = float(last["ema_slow"])
        stoch_rsi = float(last.get("stoch_rsi", 0.5))

        bull_score = 0
        bear_score = 0

        if ema_fast > ema_slow:
            bull_score += 1
        elif ema_fast < ema_slow:
            bear_score += 1

        if close > prev_close and prev_close > prev2_close:
            bull_score += 1
        elif close < prev_close and prev_close < prev2_close:
            bear_score += 1

        if 40 <= rsi <= 65:
            bull_score += 1
        elif 35 <= rsi <= 60:
            pass
        if rsi < 40:
            bear_score += 1
        if rsi > 60:
            bull_score += 1

        if macd_hist > 0:
            bull_score += 1
        elif macd_hist < 0:
            bear_score += 1

        if stoch_rsi > 0.5:
            bull_score += 1
        elif stoch_rsi < 0.5:
            bear_score += 1

        if bull_score >= 3 and bear_score <= 1:
            confidence = min(1.0, bull_score / 5.0)
            return CandidateSignal(
                self.name,
                Signal.BUY,
                confidence,
                f"Bullish momentum ({bull_score}/5 signals aligned)",
                atr * 1.5,
                atr * 2.5,
            )

        if bear_score >= 3 and bull_score <= 1:
            confidence = min(1.0, bear_score / 5.0)
            return CandidateSignal(
                self.name,
                Signal.SELL,
                confidence,
                f"Bearish momentum ({bear_score}/5 signals aligned)",
                atr * 1.5,
                atr * 2.5,
            )

        return hold(self.name, f"No clear momentum (bull={bull_score}, bear={bear_score})")
