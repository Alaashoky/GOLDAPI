"""Multi-timeframe confluence strategy."""

from __future__ import annotations

from goldbot.execution.order_models import CandidateSignal, Signal
from goldbot.strategies.base import Strategy, hold


class MTFConfluenceStrategy(Strategy):
    name = "mtf_confluence"

    def evaluate(self, bars: list[dict]) -> CandidateSignal:
        return hold(self.name, "Requires multi-timeframe data")

    def evaluate_multi(self, multi_tf_data: dict[str, dict]) -> CandidateSignal:
        h4 = multi_tf_data.get("H4", {}).get("candles", [])
        h1 = multi_tf_data.get("H1", {}).get("candles", [])
        m15 = multi_tf_data.get("M15", {}).get("candles", [])
        if not h4 or not h1 or not m15:
            return hold(self.name, "Missing timeframe candles")

        h4_last = h4[-1]
        h1_last = h1[-1]
        m15_last = m15[-1]
        atr = max(1e-6, float(m15_last["atr"]))
        price = float(m15_last["close"])

        bullish = (
            float(h4_last["ema_fast"]) > float(h4_last["ema_slow"])
            and float(h1_last["ema_fast"]) > float(h1_last["ema_slow"])
            and float(m15_last["ema_fast"]) > float(m15_last["ema_slow"])
        )
        bearish = (
            float(h4_last["ema_fast"]) < float(h4_last["ema_slow"])
            and float(h1_last["ema_fast"]) < float(h1_last["ema_slow"])
            and float(m15_last["ema_fast"]) < float(m15_last["ema_slow"])
        )

        factors = 5
        if bullish:
            confirms = 3
            if float(m15_last["rsi"]) < 60:
                confirms += 1
            if abs(price - float(m15_last["pivot_s1"])) <= (0.5 * atr):
                confirms += 1
            if confirms >= 3:
                confidence = confirms / factors
                return CandidateSignal(
                    self.name,
                    Signal.BUY,
                    confidence,
                    "Bullish alignment across H4/H1/M15 with M15 support confluence",
                    max(0.1, 1.5 * atr),
                    max(0.1, 3.0 * atr),
                )
        if bearish:
            confirms = 3
            if float(m15_last["rsi"]) > 40:
                confirms += 1
            if abs(price - float(m15_last["pivot_r1"])) <= (0.5 * atr):
                confirms += 1
            if confirms >= 3:
                confidence = confirms / factors
                return CandidateSignal(
                    self.name,
                    Signal.SELL,
                    confidence,
                    "Bearish alignment across H4/H1/M15 with M15 resistance confluence",
                    max(0.1, 1.5 * atr),
                    max(0.1, 3.0 * atr),
                )

        return hold(self.name, "No multi-timeframe confluence setup")
