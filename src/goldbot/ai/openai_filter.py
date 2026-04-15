"""Legacy compatibility module (AI-first bot now uses MarketAnalyzer)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from goldbot.ai.analyzer import MarketAnalyzer


class AIDecision(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"


@dataclass(slots=True)
class AIFilterResult:
    decision: AIDecision
    reason: str
    risk_flags: list[str]
    raw: str


class OpenAIFilter:
    def __init__(
        self,
        api_key: str,
        model: str,
        enabled: bool = True,
        timeout_seconds: int = 8,
        retries: int = 1,
        fail_behavior: str = "reject",
    ) -> None:
        self.enabled = enabled
        self.fail_behavior = fail_behavior
        self.analyzer = MarketAnalyzer(api_key=api_key, model=model, timeout_seconds=timeout_seconds, retries=retries)

    def analyze(self, market_summary: str, signal) -> AIFilterResult:  # pragma: no cover - compatibility only
        if not self.enabled:
            return AIFilterResult(AIDecision.REJECT, "AI disabled", [], "")
        analysis = self.analyzer.analyze(
            symbol="XAUUSD",
            timeframes={"M15": {"trend": "neutral", "candles": [{"summary": market_summary}]}},
            news=[],
            trade_history=[],
            performance_summary={},
        )
        if analysis.action.value in {"BUY", "SELL"}:
            return AIFilterResult(AIDecision.APPROVE, analysis.reasoning, analysis.risk_factors, analysis.raw)
        return AIFilterResult(AIDecision.REJECT, analysis.reasoning, analysis.risk_factors, analysis.raw)
