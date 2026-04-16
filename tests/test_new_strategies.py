from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from goldbot.execution.models import Signal
from goldbot.strategies.fibonacci_pullback import FibonacciPullbackStrategy
from goldbot.strategies.mean_reversion_rsi_bb import MeanReversionRSIBBStrategy
from goldbot.strategies.momentum import MomentumStrategy
from goldbot.strategies.mtf_confluence import MTFConfluenceStrategy
from goldbot.strategies.order_block import OrderBlockStrategy
from goldbot.strategies.pivot_bounce import PivotBounceStrategy
from goldbot.strategies.session_breakout import SessionBreakoutStrategy


class NewStrategiesTests(unittest.TestCase):
    def test_fibonacci_pullback_buy(self) -> None:
        bars = []
        for i in range(20):
            bars.append(
                {
                    "high": 100 + i * 0.5,
                    "low": 95 + i * 0.5,
                    "close": 100 + i * 0.5,
                    "ema_fast": 110.0,
                    "ema_slow": 105.0,
                    "rsi": 50.0,
                    "atr": 2.0,
                }
            )
        bars[-1]["close"] = 103.0
        strategy = FibonacciPullbackStrategy(lookback=20)
        signal = strategy.evaluate(bars)
        self.assertEqual(signal.signal, Signal.BUY)

    def test_session_breakout_buy(self) -> None:
        bars = []
        for hour in range(0, 12):
            ts = datetime(2026, 4, 15, hour, 0, tzinfo=timezone.utc).timestamp()
            bars.append(
                {
                    "time": ts,
                    "open": 100.0,
                    "high": 102.0 if hour < 6 else 106.0,
                    "low": 98.0,
                    "close": 101.0 if hour < 6 else 105.5,
                    "atr": 5.0,
                }
            )
        signal = SessionBreakoutStrategy().evaluate(bars)
        self.assertEqual(signal.signal, Signal.BUY)

    def test_order_block_buy(self) -> None:
        bars = [
            {"open": 10.5, "close": 10.2, "high": 10.6, "low": 10.1, "atr": 0.2},
            {"open": 10.2, "close": 9.9, "high": 10.3, "low": 9.8, "atr": 0.2},
            {"open": 9.9, "close": 9.6, "high": 10.0, "low": 9.5, "atr": 0.2},
            {"open": 9.6, "close": 9.3, "high": 9.7, "low": 9.2, "atr": 0.2},
            {"open": 9.3, "close": 9.0, "high": 9.4, "low": 8.9, "atr": 0.2},
            {"open": 9.0, "close": 8.7, "high": 9.1, "low": 8.6, "atr": 0.2},
            {"open": 9.2, "close": 8.9, "high": 9.3, "low": 8.8, "atr": 0.2},
            {"open": 9.4, "close": 9.9, "high": 10.0, "low": 9.4, "atr": 0.2},
            {"open": 9.9, "close": 10.4, "high": 10.5, "low": 9.9, "atr": 0.2},
            {"open": 10.4, "close": 10.9, "high": 11.0, "low": 10.4, "atr": 0.2},
            {"open": 10.9, "close": 9.0, "high": 11.0, "low": 8.9, "atr": 0.2},
        ]
        signal = OrderBlockStrategy().evaluate(bars)
        self.assertEqual(signal.signal, Signal.BUY)

    def test_mtf_confluence_buy(self) -> None:
        multi = {
            "H4": {"candles": [{"ema_fast": 110, "ema_slow": 100}]},
            "H1": {"candles": [{"ema_fast": 111, "ema_slow": 101}]},
            "M15": {"candles": [{"ema_fast": 112, "ema_slow": 102, "rsi": 55, "pivot_s1": 99.8, "pivot_r1": 105, "close": 100, "atr": 1.0}]},
        }
        signal = MTFConfluenceStrategy().evaluate_multi(multi)
        self.assertEqual(signal.signal, Signal.BUY)

    def test_pivot_bounce_sell(self) -> None:
        bars = []
        for _ in range(9):
            bars.append(
                {
                    "close": 105.2,
                    "pivot": 103.0,
                    "pivot_r1": 105.0,
                    "pivot_s1": 101.0,
                    "ema_fast": 100.0,
                    "ema_slow": 104.0,
                    "atr": 1.0,
                }
            )
        bars.append(
            {
                "close": 104.8,
                "pivot": 103.0,
                "pivot_r1": 105.0,
                "pivot_s1": 101.0,
                "ema_fast": 100.0,
                "ema_slow": 104.0,
                "atr": 1.0,
            }
        )
        signal = PivotBounceStrategy().evaluate(bars)
        self.assertEqual(signal.signal, Signal.SELL)

    def test_fibonacci_pullback_default_lookback_is_80(self) -> None:
        self.assertEqual(FibonacciPullbackStrategy().lookback, 80)

    def test_fibonacci_pullback_buy_with_neutral_ema(self) -> None:
        bars = [
            {"high": 110.0, "low": 100.0, "close": 109.0, "ema_fast": 106.0, "ema_slow": 106.0, "rsi": 50.0},
            {"high": 109.0, "low": 101.0, "close": 108.0, "ema_fast": 106.0, "ema_slow": 106.0, "rsi": 50.0},
            {"high": 108.0, "low": 102.0, "close": 107.0, "ema_fast": 106.0, "ema_slow": 106.0, "rsi": 50.0},
            {"high": 107.0, "low": 103.0, "close": 106.0, "ema_fast": 106.0, "ema_slow": 106.0, "rsi": 50.0},
            {"high": 106.0, "low": 104.0, "close": 105.0, "ema_fast": 104.99, "ema_slow": 105.01, "rsi": 50.0},
        ]
        signal = FibonacciPullbackStrategy(lookback=5).evaluate(bars)
        self.assertEqual(signal.signal, Signal.BUY)

    def test_mean_reversion_buy_allows_atr_proximity(self) -> None:
        bars = [
            {
                "close": 100.15,
                "bb_lower": 100.0,
                "bb_upper": 101.0,
                "rsi": 35.0,
                "atr": 1.0,
            },
            {
                "close": 100.15,
                "bb_lower": 100.0,
                "bb_upper": 101.0,
                "rsi": 35.0,
                "atr": 1.0,
            },
        ]
        signal = MeanReversionRSIBBStrategy().evaluate(bars)
        self.assertEqual(signal.signal, Signal.BUY)

    def test_pivot_bounce_sell_allows_proximity_zone(self) -> None:
        bars = []
        for _ in range(9):
            bars.append(
                {
                    "close": 105.2,
                    "pivot": 103.0,
                    "pivot_r1": 105.0,
                    "pivot_s1": 101.0,
                    "ema_fast": 100.0,
                    "ema_slow": 104.0,
                    "atr": 1.0,
                }
            )
        bars.append(
            {
                "close": 104.9,
                "pivot": 103.0,
                "pivot_r1": 105.0,
                "pivot_s1": 101.0,
                "ema_fast": 100.0,
                "ema_slow": 104.0,
                "atr": 1.0,
            }
        )
        signal = PivotBounceStrategy().evaluate(bars)
        self.assertEqual(signal.signal, Signal.SELL)

    def test_order_block_allows_lower_thrust_without_three_same_direction_candles(self) -> None:
        bars = [
            {"open": 103.0, "close": 103.0, "high": 103.2, "low": 102.8, "atr": 1.0},
            {"open": 102.0, "close": 102.1, "high": 102.3, "low": 101.9, "atr": 1.0},
            {"open": 100.0, "close": 99.5, "high": 100.0, "low": 99.0, "atr": 1.0},
            {"open": 100.2, "close": 100.8, "high": 101.0, "low": 100.2, "atr": 1.0},
            {"open": 100.8, "close": 100.6, "high": 101.0, "low": 100.5, "atr": 1.0},
            {"open": 100.6, "close": 101.1, "high": 101.2, "low": 100.6, "atr": 1.0},
            {"open": 101.1, "close": 101.0, "high": 101.3, "low": 100.9, "atr": 1.0},
            {"open": 99.8, "close": 99.7, "high": 100.0, "low": 99.5, "atr": 1.0},
        ]
        signal = OrderBlockStrategy().evaluate(bars)
        self.assertEqual(signal.signal, Signal.BUY)

    def test_mtf_confluence_accepts_three_confirms(self) -> None:
        multi = {
            "H4": {"candles": [{"ema_fast": 110, "ema_slow": 100}]},
            "H1": {"candles": [{"ema_fast": 111, "ema_slow": 101}]},
            "M15": {"candles": [{"ema_fast": 112, "ema_slow": 102, "rsi": 70, "pivot_s1": 90, "pivot_r1": 120, "close": 100, "atr": 1.0}]},
        }
        signal = MTFConfluenceStrategy().evaluate_multi(multi)
        self.assertEqual(signal.signal, Signal.BUY)

    def test_momentum_strategy_buy(self) -> None:
        bars = [
            {"close": 100.0, "ema_fast": 99.0, "ema_slow": 100.0, "rsi": 45.0, "macd_hist": 0.0, "stoch_rsi": 0.4, "atr": 1.0},
            {"close": 100.5, "ema_fast": 100.0, "ema_slow": 100.0, "rsi": 46.0, "macd_hist": 0.0, "stoch_rsi": 0.5, "atr": 1.0},
            {"close": 101.0, "ema_fast": 100.8, "ema_slow": 100.5, "rsi": 55.0, "macd_hist": 0.3, "stoch_rsi": 0.7, "atr": 1.2},
            {"close": 101.5, "ema_fast": 100.9, "ema_slow": 100.6, "rsi": 55.0, "macd_hist": 0.3, "stoch_rsi": 0.7, "atr": 1.2},
            {"close": 102.0, "ema_fast": 101.0, "ema_slow": 100.7, "rsi": 55.0, "macd_hist": 0.3, "stoch_rsi": 0.7, "atr": 1.2},
        ]
        signal = MomentumStrategy().evaluate(bars)
        self.assertEqual(signal.signal, Signal.BUY)

    def test_momentum_strategy_hold_when_mixed(self) -> None:
        bars = [
            {"close": 100.0, "ema_fast": 100.0, "ema_slow": 100.0, "rsi": 50.0, "macd_hist": 0.0, "stoch_rsi": 0.5, "atr": 1.0},
            {"close": 100.0, "ema_fast": 100.0, "ema_slow": 100.0, "rsi": 50.0, "macd_hist": 0.0, "stoch_rsi": 0.5, "atr": 1.0},
            {"close": 100.0, "ema_fast": 100.0, "ema_slow": 100.0, "rsi": 50.0, "macd_hist": 0.0, "stoch_rsi": 0.5, "atr": 1.0},
            {"close": 100.0, "ema_fast": 100.0, "ema_slow": 100.0, "rsi": 50.0, "macd_hist": 0.0, "stoch_rsi": 0.5, "atr": 1.0},
            {"close": 100.0, "ema_fast": 100.0, "ema_slow": 100.0, "rsi": 50.0, "macd_hist": 0.0, "stoch_rsi": 0.5, "atr": 1.0},
        ]
        signal = MomentumStrategy().evaluate(bars)
        self.assertEqual(signal.signal, Signal.HOLD)


if __name__ == "__main__":
    unittest.main()
