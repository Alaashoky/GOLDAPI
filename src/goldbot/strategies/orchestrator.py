"""Strategy orchestrator for hybrid signal generation."""

from __future__ import annotations

from dataclasses import dataclass

from goldbot.execution.models import CandidateSignal, Signal
from goldbot.strategies.base import Strategy, hold
from goldbot.strategies.regime_selector import RegimeSelector


@dataclass(slots=True)
class StrategyRun:
    strategy: str
    signal: CandidateSignal
    blocked: bool


class StrategyOrchestrator:
    """Runs all strategies, filters by regime, returns best signal."""

    def __init__(self, strategies: list[Strategy], regime_selector: RegimeSelector) -> None:
        self.strategies = strategies
        self.regime_selector = regime_selector

    def evaluate_with_details(
        self, bars: list[dict], multi_tf_data: dict[str, dict] | None = None
    ) -> tuple[str, list[StrategyRun]]:
        regime = self.regime_selector.classify(bars)
        allowed = self.regime_selector.allowed_strategies(regime)
        runs: list[StrategyRun] = []
        for strategy in self.strategies:
            if strategy.name not in allowed:
                runs.append(StrategyRun(strategy.name, hold(strategy.name, "Blocked by regime"), True))
                continue
            if strategy.name == "mtf_confluence" and multi_tf_data and hasattr(strategy, "evaluate_multi"):
                signal = strategy.evaluate_multi(multi_tf_data)  # type: ignore[attr-defined]
            else:
                signal = strategy.evaluate(bars)
            runs.append(StrategyRun(strategy.name, signal, False))
        return regime, runs

    def evaluate_all(self, bars: list[dict], multi_tf_data: dict[str, dict] | None = None) -> list[CandidateSignal]:
        _, runs = self.evaluate_with_details(bars, multi_tf_data)
        signals = [run.signal for run in runs if run.signal.signal != Signal.HOLD and not run.blocked]
        signals.sort(key=lambda s: s.confidence, reverse=True)
        return signals

    def best_signal(self, bars: list[dict], multi_tf_data: dict[str, dict] | None = None) -> CandidateSignal | None:
        signals = self.evaluate_all(bars, multi_tf_data)
        return signals[0] if signals else None
