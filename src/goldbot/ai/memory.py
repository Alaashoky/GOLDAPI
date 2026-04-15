"""SQLite trade memory for AI feedback loops."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import sqlite3

from goldbot.execution.models import AIAnalysis, TradeSignal


class TradeMemory:
    SUMMARY_WINDOW = 1000

    def __init__(self, db_path: str) -> None:
        self.db_path = Path(db_path)
        self.available = True
        self._initialize()

    def _initialize(self) -> None:
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS ai_memory (
                        timestamp TEXT,
                        analysis_json TEXT,
                        signal TEXT,
                        confidence INTEGER,
                        entry REAL,
                        sl REAL,
                        tp REAL,
                        outcome TEXT,
                        pnl REAL
                    )
                    """
                )
        except Exception:
            self.available = False
            logging.getLogger("goldbot").warning("Memory initialization failed", exc_info=True)

    def record_analysis(self, analysis: AIAnalysis, signal: TradeSignal, outcome: str = "PENDING", pnl: float = 0.0) -> None:
        if not self.available:
            return
        try:
            payload = {
                "trend": analysis.trend,
                "support_levels": analysis.support_levels,
                "resistance_levels": analysis.resistance_levels,
                "risk_factors": analysis.risk_factors,
                "news_impact": analysis.news_impact,
                "confidence": analysis.confidence,
                "action": analysis.action.value,
                "reasoning": analysis.reasoning,
                "entry": analysis.entry,
                "sl": analysis.sl,
                "tp": analysis.tp,
            }
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO ai_memory VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        datetime.now(tz=timezone.utc).isoformat(),
                        json.dumps(payload, ensure_ascii=False),
                        signal.signal.value,
                        signal.confidence,
                        signal.entry,
                        signal.sl,
                        signal.tp,
                        outcome,
                        pnl,
                    ),
                )
        except Exception:
            logging.getLogger("goldbot").warning("Memory record_analysis failed", exc_info=True)
            return

    def update_outcome(self, timestamp: str, outcome: str, pnl: float) -> None:
        if not self.available:
            return
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE ai_memory SET outcome = ?, pnl = ? WHERE timestamp = ?",
                    (outcome, pnl, timestamp),
                )
        except Exception:
            logging.getLogger("goldbot").warning("Memory update_outcome failed", exc_info=True)
            return

    def recent_trades(self, limit: int = 20) -> list[dict]:
        if not self.available:
            return []
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.execute(
                    "SELECT timestamp, signal, confidence, entry, sl, tp, outcome, pnl, analysis_json "
                    "FROM ai_memory ORDER BY timestamp DESC LIMIT ?",
                    (limit,),
                )
                rows = cur.fetchall()
            out = []
            for row in rows:
                out.append(
                    {
                        "timestamp": row[0],
                        "signal": row[1],
                        "confidence": row[2],
                        "entry": row[3],
                        "sl": row[4],
                        "tp": row[5],
                        "outcome": row[6],
                        "pnl": row[7],
                        "analysis": json.loads(row[8]) if row[8] else {},
                    }
                )
            return out
        except Exception:
            logging.getLogger("goldbot").warning("Memory recent_trades read failed", exc_info=True)
            return []

    def performance_summary(self) -> dict:
        trades = self.recent_trades(limit=self.SUMMARY_WINDOW)
        closed = [t for t in trades if t["outcome"] in {"WIN", "LOSS", "CLOSED", "REJECTED"}]
        if not closed:
            return {"trades": 0, "win_rate": 0.0, "avg_pnl": 0.0, "total_pnl": 0.0}
        wins = [t for t in closed if float(t["pnl"] or 0.0) > 0]
        pnls = [float(t["pnl"] or 0.0) for t in closed]
        return {
            "trades": len(closed),
            "win_rate": len(wins) / len(closed),
            "avg_pnl": sum(pnls) / len(pnls),
            "total_pnl": sum(pnls),
        }
