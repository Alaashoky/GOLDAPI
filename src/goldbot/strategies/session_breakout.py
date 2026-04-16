"""Asian session range breakout strategy."""

from __future__ import annotations

from datetime import datetime, timezone

from goldbot.execution.order_models import CandidateSignal, Signal
from goldbot.strategies.base import Strategy, hold


def _utc_hour(ts: object) -> int | None:
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(float(ts), tz=timezone.utc).hour
    if isinstance(ts, str):
        text = ts.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(text).astimezone(timezone.utc).hour
        except ValueError:
            return None
    return None


class SessionBreakoutStrategy(Strategy):
    name = "session_breakout"

    def evaluate(self, bars: list[dict]) -> CandidateSignal:
        if len(bars) < 12:
            return hold(self.name, "Not enough bars")
        last = bars[-1]
        current_hour = _utc_hour(last.get("time"))
        if current_hour is None or not (6 <= current_hour < 14):
            return hold(self.name, "Outside London session")

        asian = [b for b in bars if (hour := _utc_hour(b.get("time"))) is not None and 0 <= hour < 6]
        if len(asian) < 4:
            return hold(self.name, "No Asian session range")

        asian_high = max(float(b["high"]) for b in asian)
        asian_low = min(float(b["low"]) for b in asian)
        range_size = asian_high - asian_low
        atr = max(1e-6, float(last["atr"]))
        if range_size <= 0.3 * atr:
            return hold(self.name, "Asian range too small")

        close = float(last["close"])
        if close > asian_high:
            return CandidateSignal(
                self.name,
                Signal.BUY,
                min(1.0, 0.6 + (close - asian_high) / max(range_size, 1e-6)),
                "London breakout above Asian range",
                max(0.1, close - asian_low),
                max(0.1, range_size * 2.0),
            )
        if close < asian_low:
            return CandidateSignal(
                self.name,
                Signal.SELL,
                min(1.0, 0.6 + (asian_low - close) / max(range_size, 1e-6)),
                "London breakout below Asian range",
                max(0.1, asian_high - close),
                max(0.1, range_size * 2.0),
            )
        return hold(self.name, "No Asian range breakout")
