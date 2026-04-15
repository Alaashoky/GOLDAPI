"""Main AI-first bot runner for single-run and loop modes."""

from __future__ import annotations

from datetime import datetime, timezone
import signal
import time

from goldbot.ai.analyzer import MarketAnalyzer
from goldbot.ai.memory import TradeMemory
from goldbot.ai.signal_generator import AISignalGenerator
from goldbot.config.settings import Settings
from goldbot.data.multi_timeframe import fetch_multi_timeframe_data
from goldbot.data.mt5_adapter import MT5DataAdapter
from goldbot.data.news_feed import NewsFeed
from goldbot.execution.models import OrderRequest, Signal
from goldbot.execution.mt5_executor import MT5Executor
from goldbot.ops.alerts import TelegramAlerter
from goldbot.ops.journal import TradeJournal
from goldbot.ops.logger import get_logger
from goldbot.risk.guardrails import RiskGuardrails
from goldbot.risk.position_sizing import calculate_position_size


class BotRunner:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.logger = get_logger()
        self.stop_requested = False

        self.data = MT5DataAdapter(settings.mt5_login, settings.mt5_password, settings.mt5_server)
        self.executor = MT5Executor(enabled=settings.mode in {"demo", "live"}, deviation=settings.execution.deviation)
        self.analyzer = MarketAnalyzer(
            api_key=settings.openai_api_key,
            model=settings.ai.model,
            timeout_seconds=settings.ai.timeout_seconds,
            retries=settings.ai.retries,
        )
        self.signal_generator = AISignalGenerator()
        self.news_feed = NewsFeed(settings.finnhub_api_key)
        self.memory = TradeMemory(settings.memory_db_path)
        self.alerter = TelegramAlerter(settings.telegram_bot_token, settings.telegram_chat_id)
        self.journal = TradeJournal(settings.journal.csv_path, settings.journal.sqlite_path)
        self.guardrails = RiskGuardrails(
            max_daily_loss_pct=settings.risk.max_daily_loss_pct,
            max_open_trades=settings.risk.max_concurrent_positions,
            max_consecutive_losses=settings.risk.max_consecutive_losses,
            cooldown_minutes=settings.risk.cooldown_minutes,
            duplicate_window_seconds=settings.risk.duplicate_window_seconds,
            account_start_balance=10000.0,
        )

    def _request_stop(self, signum: int, _frame) -> None:
        self.logger.info("Shutdown signal received", extra={"extra_data": {"signal": signum}})
        self.stop_requested = True

    def _register_signal_handlers(self) -> None:
        signal.signal(signal.SIGINT, self._request_stop)
        signal.signal(signal.SIGTERM, self._request_stop)

    def run_once(self) -> None:
        self.logger.info("Run started", extra={"extra_data": {"mode": self.settings.mode, "symbol": self.settings.symbol}})
        self.data.initialize()
        try:
            self.executor.bind_mt5(self.data.mt5)
            self.data.ensure_symbol(self.settings.symbol)

            self.logger.info("Fetching multi-timeframe data")
            market_data = fetch_multi_timeframe_data(
                adapter=self.data,
                symbol=self.settings.symbol,
                timeframes=self.settings.timeframes,
                bars=self.settings.ai.analysis_bars,
            )

            self.logger.info("Fetching economic news")
            news = self.news_feed.fetch(limit=15)

            self.logger.info("Loading memory context")
            recent_history = self.memory.recent_trades(limit=20)
            performance = self.memory.performance_summary()

            self.logger.info("Requesting AI analysis")
            analysis = self.analyzer.analyze(
                symbol=self.settings.symbol,
                timeframes=market_data,
                news=news,
                trade_history=recent_history,
                performance_summary=performance,
            )
            signal_decision = self.signal_generator.generate(analysis)
            self.alerter.send_signal_analysis(self.settings.symbol, analysis, signal_decision)

            if signal_decision.signal == Signal.HOLD:
                self.logger.info("AI returned HOLD", extra={"extra_data": {"reason": signal_decision.reasoning}})
                self.memory.record_analysis(analysis, signal_decision, outcome="HOLD", pnl=0.0)
                return

            positions = self.data.open_positions(self.settings.symbol)
            account = self.data.account_info()
            balance = float(account.balance) if account else self.guardrails.account_start_balance
            equity = float(account.equity) if account else balance
            if account:
                self.guardrails.account_start_balance = balance
            daily_pnl = equity - balance
            allowed_trade, reason = self.guardrails.can_trade(
                now=datetime.now(tz=timezone.utc),
                open_positions=len(positions),
                daily_realized_pnl=daily_pnl,
                symbol=self.settings.symbol,
                direction=signal_decision.signal.value,
            )
            if not allowed_trade:
                self.logger.warning("Guardrail blocked signal", extra={"extra_data": {"reason": reason}})
                self.memory.record_analysis(analysis, signal_decision, outcome="BLOCKED", pnl=0.0)
                return

            tick = self.data.get_tick(self.settings.symbol)
            entry = float(signal_decision.entry or (tick.ask if signal_decision.signal == Signal.BUY else tick.bid))
            sl = float(signal_decision.sl or 0.0)
            tp = float(signal_decision.tp or 0.0)
            lot = calculate_position_size(
                account_balance=balance,
                risk_per_trade_pct=min(self.settings.risk.risk_per_trade_pct, self.settings.risk.max_risk_per_trade_pct),
                entry_price=entry,
                sl_price=sl,
            )

            request = OrderRequest(
                symbol=self.settings.symbol,
                signal=signal_decision.signal,
                lot=lot,
                price=entry,
                sl=sl,
                tp=tp,
                deviation=self.settings.execution.deviation,
                comment="goldbot:ai-first",
            )
            result = self.executor.place_order(request)
            now = datetime.now(tz=timezone.utc)
            self.guardrails.register_entry(now, self.settings.symbol, signal_decision.signal.value)

            self.journal.record(
                {
                    "timestamp": now.isoformat(),
                    "strategy": "ai_first",
                    "regime": analysis.trend,
                    "signal": signal_decision.signal.value,
                    "entry": entry,
                    "sl": sl,
                    "tp": tp,
                    "lot": lot,
                    "outcome": "PLACED" if result.ok else "REJECTED",
                    "pnl": 0.0,
                    "reason": result.message,
                }
            )
            self.memory.record_analysis(
                analysis,
                signal_decision,
                outcome="PLACED" if result.ok else "REJECTED",
                pnl=0.0,
            )
            self.alerter.send_execution_confirmation(self.settings.symbol, signal_decision, lot, result)
            self.logger.info("Run complete", extra={"extra_data": {"ok": result.ok, "message": result.message}})
        finally:
            self.data.shutdown()

    def run_loop(self) -> None:
        self._register_signal_handlers()
        self.logger.info("Starting loop", extra={"extra_data": {"interval_seconds": self.settings.loop_seconds}})
        while not self.stop_requested:
            try:
                self.run_once()
                self.alerter.send_daily_performance_report(self.memory.performance_summary())
            except Exception as exc:
                self.logger.exception("Loop iteration failed", extra={"extra_data": {"error": str(exc)}})
            if self.stop_requested:
                break
            time.sleep(self.settings.loop_seconds)
        self.logger.info("Loop stopped gracefully")
