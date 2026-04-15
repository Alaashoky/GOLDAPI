"""Risk guardrails and circuit breaker logic."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone


@dataclass(slots=True)
class RiskGuardrails:
    max_daily_loss_pct: float
    max_open_trades: int
    max_consecutive_losses: int
    cooldown_minutes: int
    duplicate_window_seconds: int
    account_start_balance: float
    recent_entries: dict[tuple[str, str], datetime] = field(default_factory=dict)
    consecutive_losses: int = 0
    cooldown_until: datetime | None = None

    def _daily_loss_limit(self) -> float:
        return self.account_start_balance * (self.max_daily_loss_pct / 100.0)

    def can_trade(
        self,
        now: datetime,
        open_positions: int,
        daily_realized_pnl: float,
        symbol: str,
        direction: str,
    ) -> tuple[bool, str]:
        if self.cooldown_until and now < self.cooldown_until:
            return False, f"Cooldown active until {self.cooldown_until.isoformat()}"
        if open_positions >= self.max_open_trades:
            return False, "Max concurrent positions reached"
        if daily_realized_pnl <= -self._daily_loss_limit():
            return False, "Daily loss cap reached"
        key = (symbol, direction)
        last = self.recent_entries.get(key)
        if last and (now - last).total_seconds() < self.duplicate_window_seconds:
            return False, "Duplicate entry blocked"
        return True, "OK"

    def register_entry(self, now: datetime, symbol: str, direction: str) -> None:
        self.recent_entries[(symbol, direction)] = now

    def register_trade_outcome(self, pnl: float, now: datetime | None = None) -> None:
        if pnl < 0:
            self.consecutive_losses += 1
        elif pnl > 0:
            self.consecutive_losses = 0
        if self.consecutive_losses >= self.max_consecutive_losses:
            ref = now or datetime.now(tz=timezone.utc)
            self.cooldown_until = ref + timedelta(minutes=self.cooldown_minutes)
