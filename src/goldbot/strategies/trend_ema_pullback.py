"""EMA trend pullback strategy."""

from __future__ import annotations

from goldbot.execution.order_models import CandidateSignal, Signal
from goldbot.strategies.base import Strategy, hold


class TrendEMAPullbackStrategy(Strategy):
    name = "trend_ema_pullback"
    buy_rsi_ceiling = 70
    sell_rsi_floor = 30

    def evaluate(self, bars: list[dict]) -> CandidateSignal:
        if len(bars) < 3:
            return hold(self.name, "Not enough bars")
        last = bars[-1]
        prev = bars[-2]

        trend_up = last["ema_fast"] > last["ema_slow"]
        trend_down = last["ema_fast"] < last["ema_slow"]

        pullback_buy = trend_up and last["low"] <= last["ema_fast"] <= last["close"] and last["rsi"] < self.buy_rsi_ceiling
        pullback_sell = trend_down and last["high"] >= last["ema_fast"] >= last["close"] and last["rsi"] > self.sell_rsi_floor

        confidence = min(1.0, abs(last["ema_fast"] - last["ema_slow"]) / max(1e-6, last["atr"]))

        if pullback_buy and prev["close"] < prev["ema_fast"]:
            return CandidateSignal(self.name, Signal.BUY, confidence, "Uptrend pullback", last["atr"] * 1.5, last["atr"] * 2.0)
        if pullback_sell and prev["close"] > prev["ema_fast"]:
            return CandidateSignal(self.name, Signal.SELL, confidence, "Downtrend pullback", last["atr"] * 1.5, last["atr"] * 2.0)
        return hold(self.name, "No pullback setup")
