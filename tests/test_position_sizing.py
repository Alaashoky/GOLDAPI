from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from goldbot.risk.position_sizing import calculate_position_size


class PositionSizingTests(unittest.TestCase):
    def test_position_size_matches_expected(self) -> None:
        lot = calculate_position_size(10000, 1.0, 2300.0, 2295.0)
        self.assertEqual(lot, 0.2)

    def test_position_size_zero_on_invalid_sl(self) -> None:
        lot = calculate_position_size(10000, 1.0, 2300.0, 2300.0)
        self.assertEqual(lot, 0.0)

    def test_position_size_clamped_to_max(self) -> None:
        lot = calculate_position_size(10000, 5.0, 2300.0, 2299.9, volume_max=1.0)
        self.assertEqual(lot, 1.0)


if __name__ == "__main__":
    unittest.main()
