from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from goldbot.risk.position_sizing import calculate_position_size


class PositionSizingTests(unittest.TestCase):
    def test_position_size_positive(self) -> None:
        lot = calculate_position_size(10000, 1.0, 2300.0, 2295.0)
        self.assertGreaterEqual(lot, 0.01)

    def test_position_size_zero_on_invalid_sl(self) -> None:
        lot = calculate_position_size(10000, 1.0, 2300.0, 2300.0)
        self.assertEqual(lot, 0.0)


if __name__ == "__main__":
    unittest.main()
