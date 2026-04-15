"""Common dataclasses for strategy/execution contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class Signal(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class AIDecision(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"


@dataclass(slots=True)
class CandidateSignal:
    strategy: str
    signal: Signal
    confidence: float
    rationale: str
    sl_basis: float
    tp_basis: float


@dataclass(slots=True)
class OrderRequest:
    symbol: str
    signal: Signal
    lot: float
    price: float
    sl: float
    tp: float
    deviation: int
    comment: str = "goldbot"


@dataclass(slots=True)
class OrderResult:
    ok: bool
    message: str
    ticket: int | None = None
    retcode: int | None = None


@dataclass(slots=True)
class JournalRecord:
    timestamp: datetime
    strategy: str
    regime: str
    signal: str
    entry: float
    sl: float
    tp: float
    lot: float
    outcome: str
    pnl: float
    reason: str
    extra: dict[str, str] = field(default_factory=dict)
