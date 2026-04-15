"""Strategy interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod

from goldbot.execution.order_models import CandidateSignal, Signal


class Strategy(ABC):
    name: str

    @abstractmethod
    def evaluate(self, bars: list[dict]) -> CandidateSignal:
        raise NotImplementedError


def hold(strategy_name: str, rationale: str) -> CandidateSignal:
    return CandidateSignal(
        strategy=strategy_name,
        signal=Signal.HOLD,
        confidence=0.0,
        rationale=rationale,
        sl_basis=0.0,
        tp_basis=0.0,
    )
