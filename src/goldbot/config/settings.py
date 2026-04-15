"""Typed settings loaded from YAML defaults + environment variables."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
from typing import Any

import yaml


@dataclass(slots=True)
class RiskSettings:
    risk_per_trade_pct: float
    max_risk_per_trade_pct: float
    max_daily_loss_pct: float
    max_concurrent_positions: int
    max_consecutive_losses: int
    cooldown_minutes: int
    duplicate_window_seconds: int


@dataclass(slots=True)
class AISettings:
    model: str
    analysis_bars: int
    timeout_seconds: int
    retries: int


@dataclass(slots=True)
class ExecutionSettings:
    deviation: int
    sl_atr_mult: float
    tp_atr_mult: float


@dataclass(slots=True)
class JournalSettings:
    csv_path: str
    sqlite_path: str


@dataclass(slots=True)
class Settings:
    mode: str
    symbol: str
    loop_seconds: int
    mt5_login: int | None
    mt5_password: str
    mt5_server: str
    openai_api_key: str
    finnhub_api_key: str
    telegram_bot_token: str
    telegram_chat_id: str
    timeframes: list[str]
    ai: AISettings
    risk: RiskSettings
    execution: ExecutionSettings
    journal: JournalSettings
    memory_db_path: str


def _deep_get(data: dict[str, Any], path: str, default: Any) -> Any:
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return default
        current = current[part]
    return current


def _env(name: str, default: Any) -> Any:
    return os.getenv(name, default)


def _parse_timeframes(value: str | list[str]) -> list[str]:
    if isinstance(value, list):
        return [str(v).strip().upper() for v in value if str(v).strip()]
    return [v.strip().upper() for v in str(value).split(",") if v.strip()]


def load_settings(defaults_path: str | None = None) -> Settings:
    path = Path(defaults_path or Path(__file__).with_name("defaults.yaml"))
    defaults = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    risk = RiskSettings(
        risk_per_trade_pct=float(_env("GOLDBOT_RISK_PER_TRADE_PCT", _deep_get(defaults, "risk.risk_per_trade_pct", 0.5))),
        max_risk_per_trade_pct=float(
            _env("GOLDBOT_MAX_RISK_PER_TRADE_PCT", _deep_get(defaults, "risk.max_risk_per_trade_pct", 1.0))
        ),
        max_daily_loss_pct=float(_env("GOLDBOT_MAX_DAILY_LOSS_PCT", _deep_get(defaults, "risk.max_daily_loss_pct", 2.0))),
        max_concurrent_positions=int(
            _env("GOLDBOT_MAX_CONCURRENT_POSITIONS", _deep_get(defaults, "risk.max_concurrent_positions", 1))
        ),
        max_consecutive_losses=int(
            _env("GOLDBOT_MAX_CONSECUTIVE_LOSSES", _deep_get(defaults, "risk.max_consecutive_losses", 3))
        ),
        cooldown_minutes=int(_env("GOLDBOT_COOLDOWN_MINUTES", _deep_get(defaults, "risk.cooldown_minutes", 60))),
        duplicate_window_seconds=int(
            _env("GOLDBOT_DUPLICATE_WINDOW_SECONDS", _deep_get(defaults, "risk.duplicate_window_seconds", 120))
        ),
    )

    ai = AISettings(
        model=str(_env("GOLDBOT_AI_MODEL", _deep_get(defaults, "ai.model", "gpt-4o"))),
        analysis_bars=int(_env("GOLDBOT_AI_ANALYSIS_BARS", _deep_get(defaults, "ai.analysis_bars", 50))),
        timeout_seconds=int(_env("GOLDBOT_AI_TIMEOUT_SECONDS", _deep_get(defaults, "ai.timeout_seconds", 12))),
        retries=int(_env("GOLDBOT_AI_RETRIES", _deep_get(defaults, "ai.retries", 1))),
    )

    execution = ExecutionSettings(
        deviation=int(_env("GOLDBOT_DEVIATION", _deep_get(defaults, "execution.deviation", 20))),
        sl_atr_mult=float(_env("GOLDBOT_SL_ATR_MULT", _deep_get(defaults, "execution.sl_atr_mult", 1.5))),
        tp_atr_mult=float(_env("GOLDBOT_TP_ATR_MULT", _deep_get(defaults, "execution.tp_atr_mult", 2.0))),
    )

    journal = JournalSettings(
        csv_path=str(_env("GOLDBOT_CSV_PATH", _deep_get(defaults, "journal.csv_path", "trades.csv"))),
        sqlite_path=str(_env("GOLDBOT_SQLITE_PATH", _deep_get(defaults, "journal.sqlite_path", ""))),
    )

    return Settings(
        mode=str(_env("GOLDBOT_MODE", _deep_get(defaults, "mode", "paper"))).lower(),
        symbol=str(_env("GOLDBOT_SYMBOL", _deep_get(defaults, "symbol", "XAUUSD"))),
        loop_seconds=int(_env("GOLDBOT_LOOP_SECONDS", _deep_get(defaults, "loop_seconds", 60))),
        mt5_login=int(os.getenv("MT5_LOGIN")) if os.getenv("MT5_LOGIN") else None,
        mt5_password=os.getenv("MT5_PASSWORD", ""),
        mt5_server=os.getenv("MT5_SERVER", ""),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        finnhub_api_key=os.getenv("FINNHUB_API_KEY", ""),
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
        timeframes=_parse_timeframes(_env("GOLDBOT_TIMEFRAMES", _deep_get(defaults, "timeframes", ["M15", "H1", "H4"]))),
        ai=ai,
        risk=risk,
        execution=execution,
        journal=journal,
        memory_db_path=str(_env("GOLDBOT_MEMORY_DB_PATH", _deep_get(defaults, "memory.db_path", "memory.db"))),
    )
