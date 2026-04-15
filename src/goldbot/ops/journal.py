"""Trade journaling (CSV + optional SQLite)."""

from __future__ import annotations

import csv
from pathlib import Path
import sqlite3


FIELDS = [
    "timestamp",
    "strategy",
    "regime",
    "signal",
    "entry",
    "sl",
    "tp",
    "lot",
    "outcome",
    "pnl",
    "reason",
]


class TradeJournal:
    def __init__(self, csv_path: str, sqlite_path: str = "") -> None:
        self.csv_path = Path(csv_path)
        self.sqlite_path = Path(sqlite_path) if sqlite_path else None
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.csv_path.exists():
            with self.csv_path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=FIELDS)
                writer.writeheader()
        if self.sqlite_path:
            self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(self.sqlite_path) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS journal (
                        timestamp TEXT,
                        strategy TEXT,
                        regime TEXT,
                        signal TEXT,
                        entry REAL,
                        sl REAL,
                        tp REAL,
                        lot REAL,
                        outcome TEXT,
                        pnl REAL,
                        reason TEXT
                    )
                    """
                )

    def record(self, row: dict) -> None:
        compact = {k: row.get(k, "") for k in FIELDS}
        with self.csv_path.open("a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS)
            writer.writerow(compact)
        if self.sqlite_path:
            with sqlite3.connect(self.sqlite_path) as conn:
                conn.execute(
                    "INSERT INTO journal VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    tuple(compact[k] for k in FIELDS),
                )
