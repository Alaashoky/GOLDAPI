from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from goldbot.strategies.regime_selector import RegimeSelector


class RegimeSelectorTests(unittest.TestCase):
    def test_classifies_trending(self) -> None:
        selector = RegimeSelector(trend_threshold=0.001, high_vol_threshold=0.5)
        bars = [{"close": 2000.0, "atr": 1.0, "ema_fast": 2015.0, "ema_slow": 1990.0}]
        self.assertEqual(selector.classify(bars), "TRENDING")

    def test_classifies_high_vol(self) -> None:
        selector = RegimeSelector(trend_threshold=0.5, high_vol_threshold=0.002)
        bars = [{"close": 2000.0, "atr": 10.0, "ema_fast": 2001.0, "ema_slow": 2000.0}]
        self.assertEqual(selector.classify(bars), "HIGH_VOL")


if __name__ == "__main__":
    unittest.main()
