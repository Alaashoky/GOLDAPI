"""Liquidity sweep (Smart Money Concepts) strategy."""

from __future__ import annotations

from goldbot.execution.order_models import CandidateSignal, Signal
from goldbot.strategies.base import Strategy, hold


class LiquiditySweepStrategy(Strategy):
    name = "liquidity_sweep"

    def __init__(self, swing_lookback: int = 5, confirmation_bars: int = 3) -> None:
        self.swing_lookback = swing_lookback
        self.confirmation_bars = confirmation_bars

    def _find_swing_highs(self, bars: list[dict], lookback: int) -> list[float]:
        highs: list[float] = []
        for i in range(lookback, len(bars) - lookback):
            high = float(bars[i]["high"])
            is_swing = True
            for j in range(i - lookback, i + lookback + 1):
                if j == i:
                    continue
                if j < 0 or j >= len(bars) or float(bars[j]["high"]) > high:
                    is_swing = False
                    break
            if is_swing:
                highs.append(high)
        return highs

    def _find_swing_lows(self, bars: list[dict], lookback: int) -> list[float]:
        lows: list[float] = []
        for i in range(lookback, len(bars) - lookback):
            low = float(bars[i]["low"])
            is_swing = True
            for j in range(i - lookback, i + lookback + 1):
                if j == i:
                    continue
                if j < 0 or j >= len(bars) or float(bars[j]["low"]) < low:
                    is_swing = False
                    break
            if is_swing:
                lows.append(low)
        return lows

    def evaluate(self, bars: list[dict]) -> CandidateSignal:
        if len(bars) < self.swing_lookback * 2 + self.confirmation_bars + 5:
            return hold(self.name, "Not enough bars")

        last = bars[-1]
        atr = max(1e-6, float(last["atr"]))
        price = float(last["close"])
        analysis_bars = bars[:-self.confirmation_bars]
        swing_highs = self._find_swing_highs(analysis_bars, self.swing_lookback)
        swing_lows = self._find_swing_lows(analysis_bars, self.swing_lookback)
        recent_bars = bars[-self.confirmation_bars - 1 :]

        for sh in sorted(swing_highs, reverse=True):
            swept = any(float(bar["high"]) > sh + 0.1 * atr for bar in recent_bars[:-1])
            if not swept:
                continue
            if price < sh and float(last["close"]) < float(last["open"]):
                sweep_distance = max(float(b["high"]) for b in recent_bars) - sh
                confidence = min(0.85, 0.65 + sweep_distance / (atr * 2))
                return CandidateSignal(
                    self.name,
                    Signal.SELL,
                    confidence,
                    f"Liquidity sweep above {sh:.2f} — price rejected back below",
                    max(0.1, (sh + atr) - price),
                    max(0.1, price - (sh - 2 * atr)),
                )

        for sl_level in sorted(swing_lows):
            swept = any(float(bar["low"]) < sl_level - 0.1 * atr for bar in recent_bars[:-1])
            if not swept:
                continue
            if price > sl_level and float(last["close"]) > float(last["open"]):
                sweep_distance = sl_level - min(float(b["low"]) for b in recent_bars)
                confidence = min(0.85, 0.65 + sweep_distance / (atr * 2))
                return CandidateSignal(
                    self.name,
                    Signal.BUY,
                    confidence,
                    f"Liquidity sweep below {sl_level:.2f} — price rejected back above",
                    max(0.1, price - (sl_level - atr)),
                    max(0.1, (sl_level + 2 * atr) - price),
                )

        return hold(self.name, "No liquidity sweep detected")
