from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from goldbot.data.mt5_adapter import MT5DataAdapter


class _FakeStructuredArray:
    class _DType:
        names = ("time", "open", "close")

    dtype = _DType()

    def __iter__(self):
        return iter([(1, 2300.0, 2301.0), (2, 2301.0, 2302.0)])

    def __len__(self) -> int:
        return 2


class _FakeMT5:
    TIMEFRAME_M15 = 15

    def __init__(self, rates):
        self._rates = rates

    def copy_rates_from_pos(self, symbol, tf, start_pos, bars):
        _ = symbol, tf, start_pos, bars
        return self._rates


class MT5AdapterRatesTests(unittest.TestCase):
    @staticmethod
    def _adapter_with_rates(rates) -> MT5DataAdapter:
        adapter = MT5DataAdapter(login=None, password="", server="")
        adapter.mt5 = _FakeMT5(rates)
        return adapter

    def test_get_rates_converts_structured_array_like_rows(self) -> None:
        adapter = self._adapter_with_rates(_FakeStructuredArray())

        rates = adapter.get_rates("XAUUSD", "M15", 2)

        self.assertEqual(
            rates,
            [
                {"time": 1, "open": 2300.0, "close": 2301.0},
                {"time": 2, "open": 2301.0, "close": 2302.0},
            ],
        )

    def test_get_rates_keeps_plain_iterable_dict_rows_supported(self) -> None:
        adapter = self._adapter_with_rates([{"time": 1, "open": 2300.0, "close": 2301.0}])

        rates = adapter.get_rates("XAUUSD", "M15", 1)

        self.assertEqual(rates, [{"time": 1, "open": 2300.0, "close": 2301.0}])


if __name__ == "__main__":
    unittest.main()
