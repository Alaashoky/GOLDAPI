from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from goldbot.execution.order_models import Signal
from goldbot.strategies.trend_ema_pullback import TrendEMAPullbackStrategy


class TrendEMAPullbackTests(unittest.TestCase):
    def test_buy_signal_on_pullback(self) -> None:
        strategy = TrendEMAPullbackStrategy()
        bars = [
            {"close": 2000.0, "low": 1998.0, "high": 2002.0, "ema_fast": 2001.0, "ema_slow": 1995.0, "rsi": 60.0, "atr": 3.0},
            {"close": 1999.0, "low": 1997.0, "high": 2000.0, "ema_fast": 2000.0, "ema_slow": 1996.0, "rsi": 55.0, "atr": 3.0},
            {"close": 2001.0, "low": 1999.0, "high": 2003.0, "ema_fast": 2000.5, "ema_slow": 1997.0, "rsi": 50.0, "atr": 3.0},
        ]
        decision = strategy.evaluate(bars)
        self.assertEqual(decision.signal, Signal.BUY)

    def test_sell_signal_on_pullback(self) -> None:
        strategy = TrendEMAPullbackStrategy()
        bars = [
            {"close": 2005.0, "low": 2003.0, "high": 2007.0, "ema_fast": 2004.0, "ema_slow": 2010.0, "rsi": 40.0, "atr": 3.0},
            {"close": 2006.0, "low": 2004.0, "high": 2008.0, "ema_fast": 2005.0, "ema_slow": 2010.5, "rsi": 45.0, "atr": 3.0},
            {"close": 2004.0, "low": 2002.0, "high": 2006.0, "ema_fast": 2005.0, "ema_slow": 2011.0, "rsi": 50.0, "atr": 3.0},
        ]
        decision = strategy.evaluate(bars)
        self.assertEqual(decision.signal, Signal.SELL)

    def test_hold_on_insufficient_bars(self) -> None:
        strategy = TrendEMAPullbackStrategy()
        decision = strategy.evaluate([{"close": 1, "low": 1, "high": 1, "ema_fast": 1, "ema_slow": 1, "rsi": 50, "atr": 1}])
        self.assertEqual(decision.signal, Signal.HOLD)


if __name__ == "__main__":
    unittest.main()
