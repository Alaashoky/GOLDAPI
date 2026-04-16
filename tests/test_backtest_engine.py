from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from goldbot.backtest.engine import BacktestEngine
from goldbot.execution.models import CandidateSignal, Signal
from goldbot.strategies.base import Strategy, hold

TEST_CONFIDENCE = 0.8
TEST_SL_BASIS = 1.0
IGNORED_TP_BASIS = 0.1


class _SingleSignalStrategy(Strategy):
    name = "test"

    def __init__(self, signal: Signal, trigger_len: int = 31) -> None:
        self.signal = signal
        self.trigger_len = trigger_len

    def evaluate(self, bars: list[dict]) -> CandidateSignal:
        if len(bars) == self.trigger_len:
            return CandidateSignal(self.name, self.signal, TEST_CONFIDENCE, "test", TEST_SL_BASIS, IGNORED_TP_BASIS)
        return hold(self.name, "wait")


class _LiquiditySweepSignalStrategy(_SingleSignalStrategy):
    name = "liquidity_sweep"


def _build_bars() -> list[dict]:
    bars = []
    for i in range(40):
        bars.append(
            {
                "time": 1_700_000_000 + i * 900,
                "open": 100.0,
                "high": 100.5,
                "low": 99.5,
                "close": 100.0,
                "atr": 1.0,
            }
        )
    bars[31]["open"] = 100.0
    bars[31]["high"] = 102.5
    bars[31]["low"] = 97.5
    return bars


class BacktestEngineEntryModelTests(unittest.TestCase):
    def test_buy_uses_next_open_and_spread_points(self) -> None:
        bars = _build_bars()
        bars[31]["high"] = 102.7
        bars[31]["low"] = 99.7
        result = BacktestEngine().run(
            bars=bars,
            strategy=_SingleSignalStrategy(Signal.BUY),
            starting_balance=10000.0,
            risk_per_trade_pct=1.0,
            entry_model="next_open",
            spread_points=60.0,
            point_value=0.01,
        )

        trade = result["trades"][0]
        self.assertEqual(trade["signal_index"], 30)
        self.assertEqual(trade["entry_index"], 31)
        self.assertAlmostEqual(trade["entry"], 100.6, places=6)
        self.assertAlmostEqual(trade["tp"] - trade["entry"], 2 * abs(trade["entry"] - trade["sl"]), places=6)
        self.assertEqual(trade["reason"], "TP")

    def test_sell_uses_next_open_and_spread_points(self) -> None:
        bars = _build_bars()
        bars[31]["low"] = 97.3
        bars[31]["high"] = 100.3
        result = BacktestEngine().run(
            bars=bars,
            strategy=_SingleSignalStrategy(Signal.SELL),
            starting_balance=10000.0,
            risk_per_trade_pct=1.0,
            entry_model="next_open",
            spread_points=60.0,
            point_value=0.01,
        )

        trade = result["trades"][0]
        self.assertEqual(trade["signal_index"], 30)
        self.assertEqual(trade["entry_index"], 31)
        self.assertAlmostEqual(trade["entry"], 99.4, places=6)
        self.assertAlmostEqual(trade["entry"] - trade["tp"], 2 * abs(trade["entry"] - trade["sl"]), places=6)
        self.assertEqual(trade["reason"], "TP")

    def test_h1_trend_filter_blocks_liquidity_sweep_buy_when_bearish(self) -> None:
        bars = _build_bars()
        result = BacktestEngine().run(
            bars=bars,
            strategy=_LiquiditySweepSignalStrategy(Signal.BUY),
            h1_trends=["bearish"] * len(bars),
        )
        self.assertEqual(result["trades"], [])

    def test_h1_trend_filter_allows_liquidity_sweep_buy_when_bullish(self) -> None:
        bars = _build_bars()
        bars[31]["high"] = 102.7
        result = BacktestEngine().run(
            bars=bars,
            strategy=_LiquiditySweepSignalStrategy(Signal.BUY),
            h1_trends=["bullish"] * len(bars),
        )
        self.assertEqual(len(result["trades"]), 1)


if __name__ == "__main__":
    unittest.main()
