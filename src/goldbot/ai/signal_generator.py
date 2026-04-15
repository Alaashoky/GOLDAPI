"""Convert AI analysis into validated trading signals."""

from __future__ import annotations

from goldbot.execution.models import AIAnalysis, Signal, TradeSignal


class AISignalGenerator:
    def __init__(self, min_confidence: int = 50) -> None:
        self.min_confidence = min_confidence

    def generate(self, analysis: AIAnalysis) -> TradeSignal:
        if analysis.action not in {Signal.BUY, Signal.SELL}:
            return TradeSignal(Signal.HOLD, analysis.confidence, analysis.reasoning, None, None, None)

        if analysis.confidence < self.min_confidence:
            return TradeSignal(Signal.HOLD, analysis.confidence, "Confidence too low", None, None, None)

        if analysis.entry is None or analysis.sl is None or analysis.tp is None:
            return TradeSignal(Signal.HOLD, analysis.confidence, "Missing entry/SL/TP", None, None, None)

        if analysis.sl <= 0 or analysis.tp <= 0 or analysis.entry <= 0:
            return TradeSignal(Signal.HOLD, analysis.confidence, "Invalid price levels", None, None, None)

        if analysis.action == Signal.BUY and not (analysis.sl < analysis.entry < analysis.tp):
            return TradeSignal(Signal.HOLD, analysis.confidence, "Invalid BUY structure", None, None, None)

        if analysis.action == Signal.SELL and not (analysis.tp < analysis.entry < analysis.sl):
            return TradeSignal(Signal.HOLD, analysis.confidence, "Invalid SELL structure", None, None, None)

        return TradeSignal(
            signal=analysis.action,
            confidence=analysis.confidence,
            reasoning=analysis.reasoning,
            entry=analysis.entry,
            sl=analysis.sl,
            tp=analysis.tp,
        )
