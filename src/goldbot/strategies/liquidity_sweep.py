"""Liquidity sweep (Smart Money Concepts) strategy."""

from __future__ import annotations

from goldbot.execution.order_models import CandidateSignal, Signal
from goldbot.strategies.base import Strategy, hold


class LiquiditySweepStrategy(Strategy):
    name = "liquidity_sweep"
    MIN_BUFFER_BARS = 5

    def __init__(
        self,
        swing_lookback: int = 5,
        confirmation_bars: int = 3,
        sweep_threshold_multiplier: float = 0.1,
        base_confidence: float = 0.65,
        max_confidence: float = 0.85,
    ) -> None:
        self.swing_lookback = swing_lookback
        self.confirmation_bars = confirmation_bars
        self.sweep_threshold_multiplier = sweep_threshold_multiplier
        self.base_confidence = base_confidence
        self.max_confidence = max_confidence

    def _confidence_from_sweep(self, sweep_distance: float, atr: float) -> float:
        """Scale confidence by sweep size in ATR terms, capped to a conservative max."""
        safe_atr = max(1e-6, atr)
        return min(self.max_confidence, self.base_confidence + sweep_distance / (safe_atr * 2))

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
        if len(bars) < self.swing_lookback * 2 + self.confirmation_bars + self.MIN_BUFFER_BARS:
            return hold(self.name, "Not enough bars")

        last = bars[-1]
        atr = max(1e-6, float(last["atr"]))
        price = float(last["close"])
        swing_detection_bars = bars[:-self.confirmation_bars]
        swing_highs = self._find_swing_highs(swing_detection_bars, self.swing_lookback)
        swing_lows = self._find_swing_lows(swing_detection_bars, self.swing_lookback)
        sweep_window_bars = bars[-self.confirmation_bars - 1 :]
        sweep_detection_bars = sweep_window_bars[:-1]

        for sh in sorted(swing_highs, reverse=True):
            swept = any(float(bar["high"]) > sh + self.sweep_threshold_multiplier * atr for bar in sweep_detection_bars)
            if not swept:
                continue
            if price < sh and float(last["close"]) < float(last["open"]):
                sweep_distance = max(float(b["high"]) for b in sweep_window_bars) - sh
                confidence = self._confidence_from_sweep(sweep_distance, atr)
                return CandidateSignal(
                    self.name,
                    Signal.SELL,
                    confidence,
                    f"Liquidity sweep above {sh:.2f} — price rejected back below",
                    max(0.1, (sh + atr) - price),
                    max(0.1, price - (sh - 2 * atr)),
                )

        for sl_level in sorted(swing_lows):
            swept = any(float(bar["low"]) < sl_level - self.sweep_threshold_multiplier * atr for bar in sweep_detection_bars)
            if not swept:
                continue
            if price > sl_level and float(last["close"]) > float(last["open"]):
                sweep_distance = sl_level - min(float(b["low"]) for b in sweep_window_bars)
                confidence = self._confidence_from_sweep(sweep_distance, atr)
                return CandidateSignal(
                    self.name,
                    Signal.BUY,
                    confidence,
                    f"Liquidity sweep below {sl_level:.2f} — price rejected back above",
                    max(0.1, price - (sl_level - atr)),
                    max(0.1, (sl_level + 2 * atr) - price),
                )

        return hold(self.name, "No liquidity sweep detected")
