from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from goldbot.app.runner import BotRunner
from goldbot.ai.filter import FilterResult
from goldbot.execution.models import CandidateSignal, OrderResult, Signal, TradeSignal
from goldbot.strategies.orchestrator import StrategyRun


class RunnerLoggingTests(unittest.TestCase):
    def _runner(self) -> BotRunner:
        runner = BotRunner.__new__(BotRunner)
        runner.settings = SimpleNamespace(symbol="XAUUSD.m", mode="paper")
        return runner

    def test_log_strategy_signals_prints_human_readable_block(self) -> None:
        runner = self._runner()
        best = CandidateSignal(
            strategy="fibonacci_pullback",
            signal=Signal.BUY,
            confidence=0.75,
            rationale="Fib 61.8 pullback",
            sl_basis=7.0,
            tp_basis=20.0,
        )
        runs = [
            StrategyRun(strategy=best.strategy, signal=best, blocked=False),
            StrategyRun(strategy="pivot_bounce", signal=CandidateSignal("pivot_bounce", Signal.HOLD, 0.0, "Blocked by regime", 0.0, 0.0), blocked=True),
        ]

        output = StringIO()
        with redirect_stdout(output):
            runner._log_strategy_signals("TRENDING", runs, best, entry=4825.0)

        text = output.getvalue()
        self.assertIn("📐 STRATEGY SIGNALS — XAUUSD.m", text)
        self.assertIn("🏷️  Market Regime: TRENDING", text)
        self.assertIn("fibonacci_pullback", text)
        self.assertIn("✅ BEST", text)
        self.assertIn("[blocked by regime]", text)
        self.assertIn("Reason: Blocked by regime", text)

    def test_log_ai_filter_prints_human_readable_block(self) -> None:
        runner = self._runner()
        best = CandidateSignal("fibonacci_pullback", Signal.BUY, 0.75, "Fib setup", 7.0, 20.0)
        result = FilterResult(
            decision="APPROVE",
            confidence=82,
            reasoning="Strong setup",
            risk_factors=["None significant"],
            news_impact="low",
            suggested_sl=None,
            suggested_tp=None,
        )
        output = StringIO()
        with redirect_stdout(output):
            runner._log_ai_filter(result, best)
        text = output.getvalue()
        self.assertIn("🧠 AI FILTER — Evaluating: fibonacci_pullback BUY", text)
        self.assertIn("📋 Decision:     APPROVE ✅", text)

    def test_log_strategy_signals_omits_blocked_label_when_not_blocked(self) -> None:
        runner = self._runner()
        run = StrategyRun(
            strategy="mean_reversion_rsi_bb",
            signal=CandidateSignal("mean_reversion_rsi_bb", Signal.BUY, 0.65, "setup", 1.0, 1.6),
            blocked=False,
        )
        output = StringIO()
        with redirect_stdout(output):
            runner._log_strategy_signals("RANGING", [run], run.signal, entry=2000.0)
        text = output.getvalue()
        self.assertNotIn("[blocked by regime]", text)

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

    @patch("goldbot.app.runner.fetch_multi_timeframe_data")
    def test_run_once_passes_all_strategy_signals_to_ai_filter(self, mock_fetch_multi_timeframe_data) -> None:
        runner = BotRunner.__new__(BotRunner)
        runner.settings = SimpleNamespace(
            mode="paper",
            symbol="XAUUSD.m",
            timeframes=["M15"],
            ai=SimpleNamespace(analysis_bars=200),
        )
        runner.logger = SimpleNamespace(info=lambda *a, **k: None, warning=lambda *a, **k: None, exception=lambda *a, **k: None)
        runner.data = SimpleNamespace(
            mt5=object(),
            initialize=lambda: None,
            shutdown=lambda: None,
            ensure_symbol=lambda _symbol: None,
        )
        runner.executor = SimpleNamespace(bind_mt5=lambda _mt5: None)
        runner.news_feed = SimpleNamespace(fetch=lambda limit=15: [])
        recorded = {"candidate": None}
        runner.ai_filter = SimpleNamespace(
            evaluate=lambda **kwargs: (
                recorded.update({"candidate": kwargs["candidate_signal"]})
                or FilterResult("REJECT", 60, "No", [], "none", None, None)
            )
        )
        runner.memory = SimpleNamespace(
            recent_trades=lambda limit=20: [],
            performance_summary=lambda: {},
            record_analysis=lambda *a, **k: None,
        )
        runner.alerter = SimpleNamespace()
        runner.journal = SimpleNamespace()
        runner.guardrails = SimpleNamespace()
        best = CandidateSignal("momentum", Signal.BUY, 0.6, "Bullish momentum", 5.0, 8.0)
        runs = [
            StrategyRun(strategy="momentum", signal=best, blocked=False),
            StrategyRun(
                strategy="atr_vol_expansion",
                signal=CandidateSignal("atr_vol_expansion", Signal.SELL, 0.6, "Bearish expansion", 5.0, 8.0),
                blocked=False,
            ),
        ]
        runner.orchestrator = SimpleNamespace(
            evaluate_with_details=lambda bars, multi_tf_data=None: ("RANGING", runs),
            best_signal=lambda bars, multi_tf_data=None: best,
        )
        mock_fetch_multi_timeframe_data.return_value = {
            "M15": {
                "candles": [
                    {
                        "time": 1,
                        "open": 100.0,
                        "high": 101.0,
                        "low": 99.0,
                        "close": 100.5,
                        "atr": 1.0,
                        "ema_fast": 101.0,
                        "ema_slow": 100.0,
                    }
                ]
            }
        }

        runner.run_once()

        all_signals = recorded["candidate"]["all_strategy_signals"]
        self.assertEqual(len(all_signals), 2)
        self.assertEqual(all_signals[0]["strategy"], "momentum")
        self.assertEqual(all_signals[0]["signal"], "BUY")
        self.assertEqual(all_signals[1]["strategy"], "atr_vol_expansion")
        self.assertEqual(all_signals[1]["signal"], "SELL")


if __name__ == "__main__":
    unittest.main()
