from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from goldbot.execution.models import CandidateSignal, Signal
from goldbot.strategies.base import Strategy, hold
from goldbot.strategies.orchestrator import StrategyOrchestrator
from goldbot.strategies.regime_selector import RegimeSelector


class _StaticStrategy(Strategy):
    def __init__(self, name: str, signal: Signal, confidence: float = 0.5) -> None:
        self.name = name
        self._signal = signal
        self._confidence = confidence

    def evaluate(self, bars: list[dict]) -> CandidateSignal:
        if self._signal == Signal.HOLD:
            return hold(self.name, "hold")
        return CandidateSignal(self.name, self._signal, self._confidence, "ok", 1.0, 2.0)


class _FakeMTF(Strategy):
    name = "mtf_confluence"

    def evaluate(self, bars: list[dict]) -> CandidateSignal:
        return hold(self.name, "mtf only")

    def evaluate_multi(self, multi_tf_data: dict[str, dict]) -> CandidateSignal:
        return CandidateSignal(self.name, Signal.BUY, 0.9, "mtf buy", 1.0, 2.0)


class _MTFSelector(RegimeSelector):
    def allowed_strategies(self, regime: str) -> set[str]:
        return {"mtf_confluence"}


class OrchestratorTests(unittest.TestCase):
    def test_regime_selector_allows_single_strategy_per_regime(self) -> None:
        selector = RegimeSelector()
        self.assertEqual(selector.allowed_strategies("TRENDING"), {"trend_ema_pullback"})
        self.assertEqual(selector.allowed_strategies("BREAKOUT"), {"breakout_london_ny"})
        self.assertEqual(selector.allowed_strategies("RANGING"), {"mean_reversion_rsi_bb"})
        self.assertEqual(selector.allowed_strategies("UNKNOWN"), set())

    def test_best_signal_sorted_by_confidence(self) -> None:
        selector = RegimeSelector()
        strategies = [
            _StaticStrategy("trend_ema_pullback", Signal.BUY, 0.6),
            _StaticStrategy("breakout_london_ny", Signal.BUY, 0.8),
            _StaticStrategy("mean_reversion_rsi_bb", Signal.HOLD),
        ]
        orchestrator = StrategyOrchestrator(strategies, selector)
        bars = [{"close": 100.0, "atr": 0.2, "ema_fast": 101.0, "ema_slow": 100.0}]
        best = orchestrator.best_signal(bars)
        self.assertIsNotNone(best)
        assert best is not None
        self.assertEqual(best.strategy, "trend_ema_pullback")

    def test_mtf_strategy_uses_multi_tf_input(self) -> None:
        selector = _MTFSelector()
        orchestrator = StrategyOrchestrator([_FakeMTF()], selector)
        bars = [{"close": 100.0, "atr": 0.1, "ema_fast": 101.0, "ema_slow": 100.0}]
        best = orchestrator.best_signal(bars, multi_tf_data={"M15": {"candles": [{}]}, "H1": {"candles": [{}]}, "H4": {"candles": [{}]}})
        self.assertIsNotNone(best)
        assert best is not None
        self.assertEqual(best.signal, Signal.BUY)

    def test_evaluate_with_details_blocks_non_selected_strategies(self) -> None:
        selector = RegimeSelector()
        strategies = [
            _StaticStrategy("trend_ema_pullback", Signal.BUY, 0.7),
            _StaticStrategy("breakout_london_ny", Signal.BUY, 0.7),
            _StaticStrategy("mean_reversion_rsi_bb", Signal.BUY, 0.7),
        ]
        orchestrator = StrategyOrchestrator(strategies, selector)
        bars = [{"close": 100.0, "atr": 0.4, "ema_fast": 100.05, "ema_slow": 100.0}]
        regime, runs = orchestrator.evaluate_with_details(bars)
        self.assertEqual(regime, "BREAKOUT")
        active = [run for run in runs if not run.blocked]
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0].strategy, "breakout_london_ny")


if __name__ == "__main__":
    unittest.main()
