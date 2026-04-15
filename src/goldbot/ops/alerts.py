"""Telegram alerts for analysis, execution, and daily reports."""

from __future__ import annotations

import logging
from urllib import parse, request

from goldbot.execution.models import AIAnalysis, OrderResult, TradeSignal


class TelegramAlerter:
    def __init__(self, token: str, chat_id: str) -> None:
        self.token = token
        self.chat_id = chat_id

    @property
    def enabled(self) -> bool:
        return bool(self.token and self.chat_id)

    def send(self, message: str) -> None:
        if not self.enabled:
            return
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = parse.urlencode({"chat_id": self.chat_id, "text": message}).encode("utf-8")
        req = request.Request(url, data=payload, method="POST")
        try:
            with request.urlopen(req, timeout=5):
                pass
        except Exception as exc:
            logging.getLogger("goldbot").warning("Telegram alert failed: %s", exc)

    def send_signal_analysis(self, symbol: str, analysis: AIAnalysis, signal: TradeSignal) -> None:
        message = (
            f"🧠 {symbol} AI Analysis\n"
            f"Trend: {analysis.trend}\n"
            f"Action: {signal.signal.value} ({signal.confidence}%)\n"
            f"News impact: {analysis.news_impact}\n"
            f"Reason: {signal.reasoning}"
        )
        self.send(message)

    def send_execution_confirmation(self, symbol: str, signal: TradeSignal, lot: float, result: OrderResult) -> None:
        icon = "✅" if result.ok else "❌"
        message = (
            f"{icon} {symbol} {signal.signal.value}\n"
            f"Lot: {lot:.2f}\n"
            f"Entry/SL/TP: {signal.entry} / {signal.sl} / {signal.tp}\n"
            f"Status: {result.message}"
        )
        self.send(message)

    def send_daily_performance_report(self, summary: dict) -> None:
        message = (
            "📊 Daily Performance\n"
            f"Trades: {summary.get('trades', 0)}\n"
            f"Win rate: {summary.get('win_rate', 0.0):.2%}\n"
            f"Avg PnL: {summary.get('avg_pnl', 0.0):.2f}\n"
            f"Total PnL: {summary.get('total_pnl', 0.0):.2f}"
        )
        self.send(message)
