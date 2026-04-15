from pathlib import Path
from types import SimpleNamespace
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from goldbot.ai.analyzer import MarketAnalyzer, _extract_json
from goldbot.execution.models import Signal


class AnalyzerTests(unittest.TestCase):
    def test_extract_json_from_fenced_block(self) -> None:
        raw = "```json\n{\"trend\":\"bullish\",\"action\":\"BUY\"}\n```"
        self.assertEqual(_extract_json(raw), '{"trend":"bullish","action":"BUY"}')

    def test_extract_json_from_text_wrapped_response(self) -> None:
        raw = "Here is the analysis:\n{\"trend\":\"neutral\",\"action\":\"HOLD\"}\nThanks."
        self.assertEqual(_extract_json(raw), '{"trend":"neutral","action":"HOLD"}')

    def test_analyze_parses_fenced_json_response(self) -> None:
        analyzer = MarketAnalyzer(api_key="", model="gpt-4o-mini")
        analyzer.client = object()
        analyzer._invoke = lambda _prompt: (
            "```json\n"
            '{"trend":"bullish","support_levels":[3210.5],"resistance_levels":[3245.0],'
            '"risk_factors":[],"news_impact":"low","confidence":72,"action":"BUY",'
            '"entry":3225.5,"sl":3210.0,"tp":3255.0,"reasoning":"breakout"}\n'
            "```"
        )
        analysis = analyzer.analyze("XAUUSD.m", {}, [], [], {})
        self.assertEqual(analysis.action, Signal.BUY)
        self.assertEqual(analysis.confidence, 72)
        self.assertEqual(analysis.entry, 3225.5)

    def test_invoke_requests_json_object_response_format(self) -> None:
        class FakeCompletions:
            def __init__(self) -> None:
                self.kwargs = None

            def create(self, **kwargs):
                self.kwargs = kwargs
                return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='{"action":"HOLD"}'))])

        completions = FakeCompletions()
        analyzer = MarketAnalyzer(api_key="", model="gpt-4o-mini")
        analyzer.client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
        analyzer._invoke("prompt")
        self.assertEqual(completions.kwargs["response_format"], {"type": "json_object"})


if __name__ == "__main__":
    unittest.main()
