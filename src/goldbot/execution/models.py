"""Common dataclasses for AI analysis and order execution contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class Signal(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass(slots=True)
class CandidateSignal:
    strategy: str
    signal: Signal
    confidence: float
    rationale: str
    sl_basis: float
    tp_basis: float


@dataclass(slots=True)
class AIAnalysis:
    trend: str
    support_levels: list[float]
    resistance_levels: list[float]
    risk_factors: list[str]
    news_impact: str
    confidence: int
    action: Signal
    reasoning: str
    entry: float | None = None
    sl: float | None = None
    tp: float | None = None
    raw: str = ""


@dataclass(slots=True)
class TradeSignal:
    signal: Signal
    confidence: int
    reasoning: str
    entry: float | None
    sl: float | None
    tp: float | None


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
