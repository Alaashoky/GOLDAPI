from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from goldbot.data.indicators import append_indicators


class IndicatorsTests(unittest.TestCase):
    def test_append_indicators_contains_ai_fields(self) -> None:
        bars = [
            {"open": 1.0, "high": 1.2, "low": 0.9, "close": 1.1, "tick_volume": 100},
            {"open": 1.1, "high": 1.3, "low": 1.0, "close": 1.2, "tick_volume": 120},
            {"open": 1.2, "high": 1.4, "low": 1.1, "close": 1.3, "tick_volume": 140},
        ]
        enriched = append_indicators(bars)
        latest = enriched[-1]
        for field in [
            "ema_fast",
            "ema_slow",
            "rsi",
            "atr",
            "bb_mid",
            "macd",
            "stoch_rsi",
            "volume_ratio",
            "pivot",
        ]:
            self.assertIn(field, latest)


if __name__ == "__main__":
    unittest.main()
