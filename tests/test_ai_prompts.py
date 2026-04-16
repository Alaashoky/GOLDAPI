import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from goldbot.ai.prompts import build_filter_prompt, build_market_analysis_prompt


class AIPromptTests(unittest.TestCase):
    def _candles(self, count: int) -> list[dict]:
        candles = []
        for i in range(count):
            candles.append(
                {
                    "time": i,
                    "open": 100.0 + i,
                    "high": 101.0 + i,
                    "low": 99.0 + i,
                    "close": 100.5 + i,
                    "rsi": 50 + (i % 10),
                    "ema_fast": 100.0 + i,
                    "ema_slow": 99.0 + i,
                    "macd_hist": 0.01 * i,
                    "atr": 1.0,
                    "pivot": 100.0,
                    "pivot_r1": 101.0,
                    "pivot_s1": 99.0,
                }
            )
        return candles

    def test_build_filter_prompt_includes_recent_candles_and_summary(self) -> None:
        prompt = build_filter_prompt(
            symbol="XAUUSD.m",
            candidate={"strategy": "fibonacci_pullback", "signal": "BUY"},
            timeframes={"M15": {"trend": "bullish", "candles": self._candles(120)}},
            news=[],
            trade_history=[],
            performance_summary={},
        )
        payload = json.loads(prompt.split("SIGNAL_CONTEXT=", 1)[1])
        tf_context = payload["market_context"]["M15"]
        self.assertIn("summary", tf_context)
        self.assertEqual(tf_context["summary"]["bars_analyzed"], 100)
        self.assertEqual(len(tf_context["recent_candles"]), 10)
        self.assertNotIn("latest", tf_context)

    def test_build_market_analysis_prompt_keeps_candles_payload_shape(self) -> None:
        prompt = build_market_analysis_prompt(
            symbol="XAUUSD.m",
            timeframes={"M15": {"trend": "bullish", "candles": self._candles(5)}},
            news=[],
            trade_history=[],
            performance_summary={},
        )
        payload = json.loads(prompt.split("CONTEXT_JSON=", 1)[1])
        self.assertIn("latest_indicators", payload["timeframes"]["M15"])
        self.assertIn("candles", payload["timeframes"]["M15"])

    def test_build_filter_prompt_includes_strategy_consensus_and_conflict_flag(self) -> None:
        all_signals = [
            {"strategy": "momentum", "signal": "BUY", "confidence": 60, "rationale": "bull", "blocked": False},
            {"strategy": "fibonacci_pullback", "signal": "BUY", "confidence": 56, "rationale": "fib", "blocked": False},
            {"strategy": "atr_vol_expansion", "signal": "SELL", "confidence": 60, "rationale": "atr", "blocked": False},
            {"strategy": "pivot_bounce", "signal": "HOLD", "confidence": 0, "rationale": "none", "blocked": False},
        ]
        prompt = build_filter_prompt(
            symbol="XAUUSD.m",
            candidate={"strategy": "atr_vol_expansion", "signal": "SELL", "all_strategy_signals": all_signals},
            timeframes={"M15": {"trend": "bearish", "candles": self._candles(20)}},
            news=[],
            trade_history=[],
            performance_summary={},
        )
        payload = json.loads(prompt.split("SIGNAL_CONTEXT=", 1)[1])
        self.assertEqual(payload["strategy_consensus"]["buy_count"], 2)
        self.assertEqual(payload["strategy_consensus"]["sell_count"], 1)
        self.assertEqual(payload["strategy_consensus"]["hold_count"], 1)
        self.assertEqual(payload["strategy_consensus"]["mode"], "multi_strategy")
        self.assertTrue(payload["strategy_consensus"]["conflicting"])
        self.assertEqual(payload["strategy_signal"]["all_strategy_signals"], all_signals)
        self.assertIn("PAPER MODE", prompt)

    def test_build_filter_prompt_includes_paper_mode_and_empty_history_note(self) -> None:
        all_signals = [{"strategy": "liquidity_sweep", "signal": "SELL", "confidence": 80, "rationale": "sweep", "blocked": False}]
        prompt = build_filter_prompt(
            symbol="XAUUSD.m",
            candidate={"strategy": "liquidity_sweep", "signal": "SELL", "all_strategy_signals": all_signals},
            timeframes={"M15": {"trend": "bearish", "candles": self._candles(20)}},
            news=[],
            trade_history=[],
            performance_summary={},
        )
        payload = json.loads(prompt.split("SIGNAL_CONTEXT=", 1)[1])
        self.assertEqual(payload["mode"], "PAPER")
        self.assertIn("Approve more freely", payload["mode_note"])
        self.assertIn("Do not penalize", payload["trade_history_note"])
        self.assertEqual(payload["strategy_consensus"]["mode"], "single_strategy")
        self.assertIn("Single strategy mode", payload["strategy_consensus_note"])


if __name__ == "__main__":
    unittest.main()
