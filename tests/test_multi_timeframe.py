from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from goldbot.data.multi_timeframe import fetch_multi_timeframe_data


class FakeAdapter:
    def get_rates(self, symbol: str, timeframe: str, bars: int) -> list[dict]:
        _ = symbol, bars
        base = 2300.0 if timeframe == "M15" else 2400.0
        return [
            {"open": base - 1, "high": base + 2, "low": base - 2, "close": base + i, "tick_volume": 100 + i}
            for i in range(5)
        ]


class MultiTimeframeTests(unittest.TestCase):
    def test_fetches_all_timeframes(self) -> None:
        assembled = fetch_multi_timeframe_data(FakeAdapter(), "XAUUSD", ["M15", "H1"], 5)
        self.assertEqual(set(assembled.keys()), {"M15", "H1"})
        self.assertIn("trend", assembled["M15"])
        self.assertEqual(len(assembled["H1"]["candles"]), 5)


if __name__ == "__main__":
    unittest.main()
