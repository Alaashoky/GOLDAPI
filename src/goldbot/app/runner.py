"""Main hybrid bot runner for single-run and loop modes."""

from __future__ import annotations

from datetime import datetime, timezone
from types import FrameType
import signal
import time

from goldbot.ai.filter import AITradeFilter, FilterResult
from goldbot.ai.memory import TradeMemory
from goldbot.config.settings import Settings
from goldbot.data.multi_timeframe import fetch_multi_timeframe_data
from goldbot.data.news_feed import NewsFeed
from goldbot.data.mt5_adapter import MT5DataAdapter
from goldbot.execution.models import AIAnalysis, CandidateSignal, OrderRequest, OrderResult, Signal, TradeSignal
from goldbot.execution.mt5_executor import MT5Executor
from goldbot.ops.alerts import TelegramAlerter
from goldbot.ops.journal import TradeJournal
from goldbot.ops.logger import get_logger
from goldbot.risk.guardrails import RiskGuardrails
from goldbot.risk.position_sizing import calculate_position_size
from goldbot.strategies.atr_vol_expansion import ATRVolExpansionStrategy
from goldbot.strategies.breakout_london_ny import BreakoutLondonNYStrategy
from goldbot.strategies.fibonacci_pullback import FibonacciPullbackStrategy
from goldbot.strategies.mean_reversion_rsi_bb import MeanReversionRSIBBStrategy
from goldbot.strategies.momentum import MomentumStrategy
from goldbot.strategies.mtf_confluence import MTFConfluenceStrategy
from goldbot.strategies.orchestrator import StrategyOrchestrator, StrategyRun
from goldbot.strategies.order_block import OrderBlockStrategy
from goldbot.strategies.pivot_bounce import PivotBounceStrategy
from goldbot.strategies.regime_selector import RegimeSelector
from goldbot.strategies.session_breakout import SessionBreakoutStrategy
from goldbot.strategies.trend_ema_pullback import TrendEMAPullbackStrategy


class BotRunner:
    _DIVIDER = "═══════════════════════════════════════════════════════"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.logger = get_logger()
        self.stop_requested = False
        self.last_daily_report_date: str | None = None

        self.data = MT5DataAdapter(settings.mt5_login, settings.mt5_password, settings.mt5_server)
        self.executor = MT5Executor(enabled=settings.mode in {"demo", "live"}, deviation=settings.execution.deviation)
        self.ai_filter = AITradeFilter(
            api_key=settings.openai_api_key,
            model=settings.ai.model,
            timeout_seconds=settings.ai.timeout_seconds,
            retries=settings.ai.retries,
        )
        self.news_feed = NewsFeed(settings.finnhub_api_key)
        self.memory = TradeMemory(settings.memory_db_path)
        self.alerter = TelegramAlerter(settings.telegram_bot_token, settings.telegram_chat_id)
        self.journal = TradeJournal(settings.journal.csv_path, settings.journal.sqlite_path)
        self.regime_selector = RegimeSelector()
        self.orchestrator = StrategyOrchestrator(
            strategies=[
                FibonacciPullbackStrategy(),
                TrendEMAPullbackStrategy(),
                OrderBlockStrategy(),
                SessionBreakoutStrategy(),
                MTFConfluenceStrategy(),
                BreakoutLondonNYStrategy(),
                ATRVolExpansionStrategy(),
                MeanReversionRSIBBStrategy(),
                PivotBounceStrategy(),
                MomentumStrategy(),
            ],
            regime_selector=self.regime_selector,
        )
        self.guardrails = RiskGuardrails(
            max_daily_loss_pct=settings.risk.max_daily_loss_pct,
            max_open_trades=settings.risk.max_concurrent_positions,
            max_consecutive_losses=settings.risk.max_consecutive_losses,
            cooldown_minutes=settings.risk.cooldown_minutes,
            duplicate_window_seconds=settings.risk.duplicate_window_seconds,
            account_start_balance=10000.0,
        )

    def _request_stop(self, signum: int, _frame: FrameType | None) -> None:
        self.logger.info("Shutdown signal received", extra={"extra_data": {"signal": signum}})
        self.stop_requested = True

    def _register_signal_handlers(self) -> None:
        signal.signal(signal.SIGINT, self._request_stop)
        signal.signal(signal.SIGTERM, self._request_stop)

    def _log_strategy_signals(self, regime: str, runs: list[StrategyRun], best: CandidateSignal | None, entry: float) -> None:
        print(self._DIVIDER)
        print(f"📐 STRATEGY SIGNALS — {self.settings.symbol}")
        print(self._DIVIDER)
        print(f"🏷️  Market Regime: {regime}")
        print(f"📊 Strategies Evaluated: {len(runs)}")
        print()
        for idx, run in enumerate(runs, start=1):
            signal = run.signal
            confidence = int(round(signal.confidence * 100))
            blocked = "  [blocked by regime]" if run.blocked else ""
            best_marker = " ✅ BEST" if best and best.strategy == signal.strategy and signal.signal != Signal.HOLD else ""
            print(f"   {idx}. {signal.strategy:<22} → {signal.signal.value:<4} ({confidence:>2}%)" f"{best_marker}{blocked}")
            if signal.signal in {Signal.BUY, Signal.SELL}:
                sl = entry - signal.sl_basis if signal.signal == Signal.BUY else entry + signal.sl_basis
                tp = entry + signal.tp_basis if signal.signal == Signal.BUY else entry - signal.tp_basis
                print(f"      Entry: {entry:.2f} | SL: {sl:.2f} | TP: {tp:.2f}")
                print(f"      Reason: {signal.rationale}")
            if signal.signal == Signal.HOLD and signal.rationale:
                print(f"      Reason: {signal.rationale}")
        print(self._DIVIDER)

    def _log_ai_filter(self, result: FilterResult, signal: CandidateSignal) -> None:
        print(self._DIVIDER)
        print(f"🧠 AI FILTER — Evaluating: {signal.strategy} {signal.signal.value}")
        print(self._DIVIDER)
        decision_icon = "✅" if result.decision == "APPROVE" else "❌"
        print(f"📋 Decision:     {result.decision} {decision_icon}")
        print(f"💪 Confidence:   {result.confidence}%")
        print(f"📰 News Impact:  {result.news_impact}")
        print("⚠️  Risk Factors:")
        if result.risk_factors:
            for factor in result.risk_factors:
                print(f"   • {factor}")
        else:
            print("   • None significant")
        print("💬 Reasoning:")
        print(f"   {result.reasoning}")
        print(self._DIVIDER)

    def _log_trade_executed(
        self,
        signal_decision: TradeSignal,
        lot: float,
        entry: float,
        sl: float,
        tp: float,
        result: OrderResult,
        strategy: str | None = None,
    ) -> None:
        mode_label = "Paper Mode" if self.settings.mode == "paper" else "Real Mode"
        risk = abs(entry - sl) * lot
        print(self._DIVIDER)
        print(f"✅ TRADE EXECUTED ({mode_label})")
        print(self._DIVIDER)
        if strategy:
            print(f"   Strategy:     {strategy}")
        print(f"   Signal:       {signal_decision.signal.value}")
        print(f"   Entry:        {entry:.2f}")
        print(f"   Stop Loss:    {sl:.2f}")
        print(f"   Take Profit:  {tp:.2f}")
        print(f"   Lot Size:     {lot:.2f}")
        print(f"   Risk:         ${risk:.2f}")
        print(f"   Result:       {result.message}")
        print(self._DIVIDER)

    def _log_hold(self, reason: str) -> None:
        print(self._DIVIDER)
        print("⏸️  HOLD — No trade")
        print(f"   Reason: {reason}")
        print(self._DIVIDER)

    def _log_blocked(self, reason: str) -> None:
        print(self._DIVIDER)
        print("🛡️ BLOCKED by Risk Guardrails")
        print(f"   Reason: {reason}")
        print(self._DIVIDER)

    def _signal_to_trade_signal(self, signal: CandidateSignal, entry: float, sl: float, tp: float) -> TradeSignal:
        return TradeSignal(
            signal=signal.signal,
            confidence=int(max(0, min(100, round(signal.confidence * 100)))),
            reasoning=signal.rationale,
            entry=entry,
            sl=sl,
            tp=tp,
        )

    def _analysis_from_filter(
        self,
        trend: str,
        result: FilterResult,
        trade_signal: TradeSignal,
        action: Signal,
        reasoning: str,
    ) -> AIAnalysis:
        return AIAnalysis(
            trend=trend,
            support_levels=[],
            resistance_levels=[],
            risk_factors=result.risk_factors,
            news_impact=result.news_impact,
            confidence=result.confidence,
            action=action,
            reasoning=reasoning,
            entry=trade_signal.entry,
            sl=trade_signal.sl,
            tp=trade_signal.tp,
            raw=result.raw,
        )

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

            m15_bars = market_data.get("M15", {}).get("candles", [])
            if not m15_bars:
                self._log_hold("No M15 candles")
                return

            regime, runs = self.orchestrator.evaluate_with_details(m15_bars, multi_tf_data=market_data)
            best = self.orchestrator.best_signal(m15_bars, multi_tf_data=market_data)
            entry_hint = float(m15_bars[-1]["close"])
            self._log_strategy_signals(regime, runs, best, entry_hint)

            if best is None:
                self._log_hold("No strategy signal")
                return

            sl_hint = entry_hint - best.sl_basis if best.signal == Signal.BUY else entry_hint + best.sl_basis
            tp_hint = entry_hint + best.tp_basis if best.signal == Signal.BUY else entry_hint - best.tp_basis
            candidate_payload = {
                "strategy": best.strategy,
                "signal": best.signal.value,
                "confidence": int(max(0, min(100, round(best.confidence * 100)))),
                "rationale": best.rationale,
                "entry": entry_hint,
                "sl": sl_hint,
                "tp": tp_hint,
            }

            filter_result = self.ai_filter.evaluate(
                symbol=self.settings.symbol,
                candidate_signal=candidate_payload,
                timeframes=market_data,
                news=news,
                trade_history=recent_history,
                performance_summary=performance,
            )
            self._log_ai_filter(filter_result, best)

            if filter_result.decision == "REJECT":
                self._log_hold(f"AI rejected: {filter_result.reasoning}")
                hold_signal = TradeSignal(Signal.HOLD, filter_result.confidence, filter_result.reasoning, None, None, None)
                analysis = self._analysis_from_filter(
                    trend=regime.lower(),
                    result=filter_result,
                    trade_signal=hold_signal,
                    action=Signal.HOLD,
                    reasoning=filter_result.reasoning,
                )
                self.memory.record_analysis(analysis, hold_signal, outcome="HOLD", pnl=0.0)
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
                direction=best.signal.value,
            )
            if not allowed_trade:
                self._log_blocked(reason)
                self.logger.warning("Guardrail blocked signal", extra={"extra_data": {"reason": reason}})
                blocked_signal = TradeSignal(
                    best.signal,
                    int(max(0, min(100, round(best.confidence * 100)))),
                    reason,
                    None,
                    None,
                    None,
                )
                blocked_analysis = self._analysis_from_filter(
                    trend=regime.lower(),
                    result=filter_result,
                    trade_signal=blocked_signal,
                    action=Signal.HOLD,
                    reasoning=reason,
                )
                self.memory.record_analysis(blocked_analysis, blocked_signal, outcome="BLOCKED", pnl=0.0)
                return

            tick = self.data.get_tick(self.settings.symbol)
            entry = float(tick.ask if best.signal == Signal.BUY else tick.bid)
            sl = float(filter_result.suggested_sl) if filter_result.suggested_sl is not None else (
                entry - best.sl_basis if best.signal == Signal.BUY else entry + best.sl_basis
            )
            tp = float(filter_result.suggested_tp) if filter_result.suggested_tp is not None else (
                entry + best.tp_basis if best.signal == Signal.BUY else entry - best.tp_basis
            )
            if best.signal == Signal.BUY and not (sl < entry < tp):
                self._log_hold("Invalid BUY SL/TP after filter")
                return
            if best.signal == Signal.SELL and not (tp < entry < sl):
                self._log_hold("Invalid SELL SL/TP after filter")
                return
            lot = calculate_position_size(
                account_balance=balance,
                risk_per_trade_pct=min(self.settings.risk.risk_per_trade_pct, self.settings.risk.max_risk_per_trade_pct),
                entry_price=entry,
                sl_price=sl,
            )
            signal_decision = self._signal_to_trade_signal(best, entry, sl, tp)

            request = OrderRequest(
                symbol=self.settings.symbol,
                signal=best.signal,
                lot=lot,
                price=entry,
                sl=sl,
                tp=tp,
                deviation=self.settings.execution.deviation,
                comment=f"goldbot:hybrid:{best.strategy}",
            )
            result = self.executor.place_order(request)
            self._log_trade_executed(signal_decision, lot, entry, sl, tp, result, strategy=best.strategy)
            now = datetime.now(tz=timezone.utc)
            self.guardrails.register_entry(now, self.settings.symbol, best.signal.value)

            self.journal.record(
                {
                    "timestamp": now.isoformat(),
                    "strategy": best.strategy,
                    "regime": regime,
                    "signal": best.signal.value,
                    "entry": entry,
                    "sl": sl,
                    "tp": tp,
                    "lot": lot,
                    "outcome": "PLACED" if result.ok else "REJECTED",
                    "pnl": 0.0,
                    "reason": filter_result.reasoning,
                }
            )
            analysis = self._analysis_from_filter(
                trend=regime.lower(),
                result=filter_result,
                trade_signal=signal_decision,
                action=best.signal,
                reasoning=filter_result.reasoning,
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
                today = datetime.now(tz=timezone.utc).date().isoformat()
                if self.last_daily_report_date != today:
                    self.alerter.send_daily_performance_report(self.memory.performance_summary())
                    self.last_daily_report_date = today
            except Exception as exc:
                self.logger.exception("Loop iteration failed")
            if self.stop_requested:
                break
            time.sleep(self.settings.loop_seconds)
        self.logger.info("Loop stopped gracefully")
