from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from goldbot.risk.guardrails import RiskGuardrails


class GuardrailsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.guardrails = RiskGuardrails(
            max_daily_loss_pct=2.0,
            max_open_trades=1,
            max_consecutive_losses=3,
            cooldown_minutes=60,
            duplicate_window_seconds=120,
            account_start_balance=10000.0,
        )

    def test_blocks_max_open_positions(self) -> None:
        ok, reason = self.guardrails.can_trade(datetime.now(tz=timezone.utc), 1, 0.0, "XAUUSD", "BUY")
        self.assertFalse(ok)
        self.assertIn("Max concurrent", reason)

    def test_blocks_daily_loss(self) -> None:
        ok, reason = self.guardrails.can_trade(datetime.now(tz=timezone.utc), 0, -500.0, "XAUUSD", "BUY")
        self.assertFalse(ok)
        self.assertIn("Daily loss", reason)

    def test_blocks_duplicate_window(self) -> None:
        now = datetime.now(tz=timezone.utc)
        self.guardrails.register_entry(now, "XAUUSD", "BUY")
        ok, reason = self.guardrails.can_trade(now + timedelta(seconds=30), 0, 0.0, "XAUUSD", "BUY")
        self.assertFalse(ok)
        self.assertIn("Duplicate", reason)

    def test_blocks_during_cooldown_after_consecutive_losses(self) -> None:
        now = datetime.now(tz=timezone.utc)
        self.guardrails.register_trade_outcome(-10.0, now=now)
        self.guardrails.register_trade_outcome(-5.0, now=now)
        self.guardrails.register_trade_outcome(-2.0, now=now)
        ok, reason = self.guardrails.can_trade(now + timedelta(minutes=1), 0, 0.0, "XAUUSD", "SELL")
        self.assertFalse(ok)
        self.assertIn("Cooldown", reason)


if __name__ == "__main__":
    unittest.main()
