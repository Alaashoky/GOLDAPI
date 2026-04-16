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
            return "BREAKOUT"
        if trend_strength >= self.trend_threshold:
            return "TRENDING"
        return "RANGING"

    def allowed_strategies(self, regime: str) -> set[str]:
        mapping = {
            "TRENDING": {"trend_ema_pullback"},
            "BREAKOUT": {"breakout_london_ny"},
            "RANGING": {"mean_reversion_rsi_bb"},
        }
        return mapping.get(regime, set())
