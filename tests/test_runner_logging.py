from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from goldbot.app.runner import BotRunner
from goldbot.execution.models import AIAnalysis, OrderResult, Signal, TradeSignal


class RunnerLoggingTests(unittest.TestCase):
    def _runner(self) -> BotRunner:
        runner = BotRunner.__new__(BotRunner)
        runner.settings = SimpleNamespace(symbol="XAUUSD.m", mode="paper")
        return runner

    def test_log_analysis_prints_human_readable_block(self) -> None:
        runner = self._runner()
        analysis = AIAnalysis(
            trend="bullish",
            support_levels=[3210.5, 3195.0],
            resistance_levels=[3245.0, 3260.0],
            risk_factors=["NFP report tomorrow", "High volatility"],
            news_impact="medium",
            confidence=72,
            action=Signal.BUY,
            reasoning="Bullish trend on H1/H4.",
            entry=3225.5,
            sl=3210.0,
            tp=3255.0,
        )
        decision = TradeSignal(Signal.BUY, 72, "Bullish trend on H1/H4.", 3225.5, 3210.0, 3255.0)

        output = StringIO()
        with redirect_stdout(output):
            runner._log_analysis(analysis, decision)

        text = output.getvalue()
        self.assertIn("🧠 AI ANALYSIS — XAUUSD.m", text)
        self.assertIn("📈 Trend:        bullish", text)
        self.assertIn("💪 Confidence:   72%", text)
        self.assertIn("📊 Support:      3210.50, 3195.00", text)
        self.assertIn("⚠️  Risk Factors:", text)
        self.assertIn("🎯 ACTION:       BUY", text)
        self.assertIn("💬 Reasoning:", text)

    def test_log_trade_executed_prints_trade_details(self) -> None:
        runner = self._runner()
        decision = TradeSignal(Signal.BUY, 72, "Bullish trend on H1/H4.", 3225.5, 3210.0, 3255.0)
        result = OrderResult(ok=True, message="Paper mode order accepted")

        output = StringIO()
        with redirect_stdout(output):
            runner._log_trade_executed(decision, lot=0.05, entry=3225.5, sl=3210.0, tp=3255.0, result=result)

        text = output.getvalue()
        self.assertIn("✅ TRADE EXECUTED (Paper Mode)", text)
        self.assertIn("   Signal:       BUY", text)
        self.assertIn("   Lot Size:     0.05", text)
        self.assertIn("   Risk:         $0.78", text)
        self.assertIn("   Result:       Paper mode order accepted", text)

    def test_log_hold_prints_reason(self) -> None:
        runner = self._runner()
        output = StringIO()
        with redirect_stdout(output):
            runner._log_hold("No clear setup, mixed signals across timeframes")
        text = output.getvalue()
        self.assertIn("⏸️  HOLD — No trade", text)
        self.assertIn("Reason: No clear setup, mixed signals across timeframes", text)

    def test_log_blocked_prints_reason(self) -> None:
        runner = self._runner()
        output = StringIO()
        with redirect_stdout(output):
            runner._log_blocked("Max daily loss reached")
        text = output.getvalue()
        self.assertIn("🛡️ BLOCKED by Risk Guardrails", text)
        self.assertIn("Reason: Max daily loss reached", text)


if __name__ == "__main__":
    unittest.main()
