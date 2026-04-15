from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from goldbot.ai.memory import TradeMemory
from goldbot.execution.models import AIAnalysis, Signal, TradeSignal


class MemoryTests(unittest.TestCase):
    def test_record_and_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            memory = TradeMemory(f"{tmp}/memory.db")
            analysis = AIAnalysis(
                trend="bullish",
                support_levels=[2300.0],
                resistance_levels=[2320.0],
                risk_factors=[],
                news_impact="medium",
                confidence=70,
                action=Signal.BUY,
                reasoning="test",
                entry=2310.0,
                sl=2305.0,
                tp=2320.0,
            )
            signal = TradeSignal(Signal.BUY, 70, "test", 2310.0, 2305.0, 2320.0)
            memory.record_analysis(analysis, signal, outcome="WIN", pnl=30.0)
            trades = memory.recent_trades(5)
            self.assertEqual(len(trades), 1)
            summary = memory.performance_summary()
            self.assertEqual(summary["trades"], 1)
            self.assertGreater(summary["win_rate"], 0.0)


if __name__ == "__main__":
    unittest.main()
