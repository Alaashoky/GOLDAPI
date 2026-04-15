"""Market regime classifier and strategy routing."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class RegimeSelector:
    trend_threshold: float = 0.001
    high_vol_threshold: float = 0.003

    def classify(self, bars: list[dict]) -> str:
        if not bars:
            return "UNKNOWN"
        last = bars[-1]
        close = max(1e-6, float(last["close"]))
        atr_ratio = float(last["atr"]) / close
        trend_strength = abs(float(last["ema_fast"]) - float(last["ema_slow"])) / close

        if atr_ratio >= self.high_vol_threshold:
            return "HIGH_VOL"
        if trend_strength >= self.trend_threshold:
            return "TRENDING"
        return "RANGING"

    def allowed_strategies(self, regime: str) -> set[str]:
        if regime == "TRENDING":
            return {"trend_ema_pullback", "breakout_london_ny", "atr_vol_expansion"}
        if regime == "HIGH_VOL":
            return {"breakout_london_ny", "atr_vol_expansion"}
        if regime == "RANGING":
            return {"mean_reversion_rsi_bb", "trend_ema_pullback"}
        return set()
