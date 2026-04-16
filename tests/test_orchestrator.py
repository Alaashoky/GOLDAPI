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


class OrchestratorTests(unittest.TestCase):
    def test_regime_selector_allows_momentum(self) -> None:
        selector = RegimeSelector()
        self.assertIn("momentum", selector.allowed_strategies("RANGING"))

    def test_best_signal_sorted_by_confidence(self) -> None:
        selector = RegimeSelector()
        strategies = [
            _StaticStrategy("trend_ema_pullback", Signal.BUY, 0.6),
            _StaticStrategy("breakout_london_ny", Signal.BUY, 0.8),
            _StaticStrategy("atr_vol_expansion", Signal.HOLD),
        ]
        orchestrator = StrategyOrchestrator(strategies, selector)
        bars = [{"close": 100.0, "atr": 0.2, "ema_fast": 101.0, "ema_slow": 100.0}]
        best = orchestrator.best_signal(bars)
        self.assertIsNotNone(best)
        assert best is not None
        self.assertEqual(best.strategy, "breakout_london_ny")

    def test_mtf_strategy_uses_multi_tf_input(self) -> None:
        selector = RegimeSelector()
        orchestrator = StrategyOrchestrator([_FakeMTF()], selector)
        bars = [{"close": 100.0, "atr": 0.1, "ema_fast": 101.0, "ema_slow": 100.0}]
        best = orchestrator.best_signal(bars, multi_tf_data={"M15": {"candles": [{}]}, "H1": {"candles": [{}]}, "H4": {"candles": [{}]}})
        self.assertIsNotNone(best)
        assert best is not None
        self.assertEqual(best.signal, Signal.BUY)

    def test_evaluate_with_details_no_longer_blocks_by_regime(self) -> None:
        selector = RegimeSelector()
        strategies = [_StaticStrategy("mean_reversion_rsi_bb", Signal.BUY, 0.7)]
        orchestrator = StrategyOrchestrator(strategies, selector)
        bars = [{"close": 100.0, "atr": 0.4, "ema_fast": 102.0, "ema_slow": 99.0}]
        _, runs = orchestrator.evaluate_with_details(bars)
        self.assertFalse(runs[0].blocked)
        self.assertEqual(runs[0].signal.signal, Signal.BUY)


if __name__ == "__main__":
    unittest.main()
