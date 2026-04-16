from pathlib import Path
from types import SimpleNamespace
import sys
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from goldbot.ai.filter import AITradeFilter

TEST_API_KEY = "fake-api-key"


class AITradeFilterTests(unittest.TestCase):
    def test_evaluate_parses_approved_json(self) -> None:
        trade_filter = AITradeFilter(api_key=TEST_API_KEY, model="gpt-4o-mini")
        trade_filter.client = SimpleNamespace()
        trade_filter._invoke = lambda _prompt: (
            '{"decision":"APPROVE","confidence":82,"reasoning":"Good setup","risk_factors":[],'
            '"news_impact":"low","suggested_sl_adjustment":4818.0,"suggested_tp_adjustment":4845.0}'
        )
        result = trade_filter.evaluate(
            symbol="XAUUSD.m",
            candidate_signal={"strategy": "fibonacci_pullback", "signal": "BUY"},
            timeframes={},
            news=[],
            trade_history=[],
            performance_summary={},
        )
        self.assertEqual(result.decision, "APPROVE")
        self.assertEqual(result.confidence, 82)
        self.assertEqual(result.suggested_sl, 4818.0)

    def test_evaluate_rejects_on_invalid_json(self) -> None:
        trade_filter = AITradeFilter(api_key=TEST_API_KEY, model="gpt-4o-mini", retries=0)
        trade_filter.client = SimpleNamespace()
        trade_filter._invoke = lambda _prompt: "not-json"
        result = trade_filter.evaluate(
            symbol="XAUUSD.m",
            candidate_signal={"strategy": "fibonacci_pullback", "signal": "BUY"},
            timeframes={},
            news=[],
            trade_history=[],
            performance_summary={},
        )
        self.assertEqual(result.decision, "REJECT")

    def test_evaluate_rejects_on_timeout_fail_closed(self) -> None:
        trade_filter = AITradeFilter(api_key=TEST_API_KEY, model="gpt-4o-mini", timeout_seconds=0.05, retries=0)
        trade_filter.client = SimpleNamespace()

        def _slow_invoke(_prompt: str) -> str:
            time.sleep(0.1)
            return '{"decision":"APPROVE"}'

        trade_filter._invoke = _slow_invoke
        result = trade_filter.evaluate(
            symbol="XAUUSD.m",
            candidate_signal={"strategy": "trend_ema_pullback", "signal": "BUY"},
            timeframes={},
            news=[],
            trade_history=[],
            performance_summary={},
        )
        self.assertEqual(result.decision, "REJECT")
        self.assertIn("timeout", result.reasoning.lower())

    def test_evaluate_rejects_on_error_fail_closed(self) -> None:
        trade_filter = AITradeFilter(api_key=TEST_API_KEY, model="gpt-4o-mini", retries=0)
        trade_filter.client = SimpleNamespace()

        def _raise_error(_prompt: str) -> str:
            raise RuntimeError("api down")

        trade_filter._invoke = _raise_error
        result = trade_filter.evaluate(
            symbol="XAUUSD.m",
            candidate_signal={"strategy": "breakout_london_ny", "signal": "SELL"},
            timeframes={},
            news=[],
            trade_history=[],
            performance_summary={},
        )
        self.assertEqual(result.decision, "REJECT")
        self.assertIn("api down", result.reasoning.lower())

    def test_invoke_requests_json_object_response_format(self) -> None:
        class FakeCompletions:
            def __init__(self) -> None:
                self.kwargs = None

            def create(self, **kwargs):
                self.kwargs = kwargs
                return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='{"decision":"REJECT"}'))])

        completions = FakeCompletions()
        trade_filter = AITradeFilter(api_key=TEST_API_KEY, model="gpt-4o-mini")
        trade_filter.client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
        raw = trade_filter._invoke("prompt")
        self.assertEqual(completions.kwargs["response_format"], {"type": "json_object"})
        self.assertEqual(raw, '{"decision":"REJECT"}')


if __name__ == "__main__":
    unittest.main()
