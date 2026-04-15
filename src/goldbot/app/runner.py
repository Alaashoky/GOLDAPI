"""Main bot runner for single-run and loop modes."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import time

from goldbot.ai.openai_filter import OpenAIFilter
from goldbot.config.settings import Settings
from goldbot.data.mt5_data import MT5DataAdapter, append_indicators
from goldbot.execution.mt5_executor import MT5Executor
from goldbot.execution.order_models import OrderRequest, Signal
from goldbot.ops.alerts import TelegramAlerter
from goldbot.ops.journal import TradeJournal
from goldbot.ops.logger import get_logger
from goldbot.risk.position_sizing import calculate_position_size
from goldbot.risk.risk_guardrails import RiskGuardrails
from goldbot.strategies.atr_vol_expansion import ATRVolExpansionStrategy
from goldbot.strategies.breakout_london_ny import BreakoutLondonNYStrategy
from goldbot.strategies.mean_reversion_rsi_bb import MeanReversionRSIBBStrategy
from goldbot.strategies.regime_selector import RegimeSelector
from goldbot.strategies.trend_ema_pullback import TrendEMAPullbackStrategy


class BotRunner:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.logger = get_logger()
        self.data = MT5DataAdapter(settings.mt5_login, settings.mt5_password, settings.mt5_server)
        self.executor = MT5Executor(enabled=settings.mode in {"demo", "live"}, deviation=settings.execution.deviation)
        self.ai = OpenAIFilter(
            api_key=settings.openai_api_key,
            model=settings.ai.model,
            enabled=settings.ai.enabled,
            timeout_seconds=settings.ai.timeout_seconds,
            retries=settings.ai.retries,
            fail_behavior=settings.ai.fail_behavior,
        )
        self.alerter = TelegramAlerter(settings.telegram_bot_token, settings.telegram_chat_id)
        self.journal = TradeJournal(settings.journal.csv_path, settings.journal.sqlite_path)
        self.regime_selector = RegimeSelector()
        self.strategies = {
            "trend_ema_pullback": TrendEMAPullbackStrategy(),
            "breakout_london_ny": BreakoutLondonNYStrategy(settings.strategy.breakout_lookback),
            "atr_vol_expansion": ATRVolExpansionStrategy(settings.strategy.atr_expansion_mult),
            "mean_reversion_rsi_bb": MeanReversionRSIBBStrategy(),
        }
        self.guardrails = RiskGuardrails(
            max_daily_loss_pct=settings.risk.max_daily_loss_pct,
            max_open_trades=settings.risk.max_concurrent_positions,
            max_consecutive_losses=settings.risk.max_consecutive_losses,
            cooldown_minutes=settings.risk.cooldown_minutes,
            duplicate_window_seconds=settings.risk.duplicate_window_seconds,
            account_start_balance=10000.0,
        )

    def _market_summary(self, last: dict, regime: str) -> str:
        return (
            f"regime={regime}, close={last['close']:.3f}, ema_fast={last['ema_fast']:.3f}, "
            f"ema_slow={last['ema_slow']:.3f}, rsi={last['rsi']:.2f}, atr={last['atr']:.3f}"
        )

    def run_once(self) -> None:
        mode = self.settings.mode
        self.logger.warning("Mode is %s (use demo before live)", mode)

        try:
            self.data.initialize()
            self.executor.bind_mt5(self.data.mt5)
            self.data.ensure_symbol(self.settings.symbol)
            bars = self.data.get_rates(self.settings.symbol, self.settings.timeframe, self.settings.bars)
            bars = append_indicators(
                bars,
                ema_fast=self.settings.strategy.ema_fast,
                ema_slow=self.settings.strategy.ema_slow,
                rsi_period=self.settings.strategy.rsi_period,
                atr_period=self.settings.strategy.atr_period,
                bb_period=self.settings.strategy.bb_period,
                bb_std=self.settings.strategy.bb_std,
            )
            regime = self.regime_selector.classify(bars)
            allowed = self.regime_selector.allowed_strategies(regime)
            decisions = [self.strategies[name].evaluate(bars) for name in allowed if name in self.strategies]
            decisions = [d for d in decisions if d.signal != Signal.HOLD]
            if not decisions:
                self.logger.info("No strategy signal", extra={"extra_data": {"regime": regime}})
                return

            decision = max(decisions, key=lambda d: d.confidence)
            now = datetime.now(tz=timezone.utc)
            positions = self.data.open_positions(self.settings.symbol)
            account = self.data.account_info()
            balance = float(account.balance) if account else self.guardrails.account_start_balance
            equity = float(account.equity) if account else balance
            if account:
                self.guardrails.account_start_balance = balance
            daily_pnl = equity - balance
            allowed_trade, reason = self.guardrails.can_trade(
                now,
                open_positions=len(positions),
                daily_realized_pnl=daily_pnl,
                symbol=self.settings.symbol,
                direction=decision.signal.value,
            )
            if not allowed_trade:
                self.logger.warning("Risk guardrail blocked", extra={"extra_data": {"reason": reason}})
                return

            summary = self._market_summary(bars[-1], regime)
            ai_result = self.ai.analyze(summary, decision)
            if ai_result.decision.value != "APPROVE":
                self.logger.warning("AI rejected signal", extra={"extra_data": asdict(ai_result)})
                return

            tick = self.data.get_tick(self.settings.symbol)
            entry = float(tick.ask if decision.signal == Signal.BUY else tick.bid)
            sl = entry - decision.sl_basis if decision.signal == Signal.BUY else entry + decision.sl_basis
            tp = entry + decision.tp_basis if decision.signal == Signal.BUY else entry - decision.tp_basis
            lot = calculate_position_size(
                account_balance=balance,
                risk_per_trade_pct=min(self.settings.risk.risk_per_trade_pct, self.settings.risk.max_risk_per_trade_pct),
                entry_price=entry,
                sl_price=sl,
            )
            request = OrderRequest(
                symbol=self.settings.symbol,
                signal=decision.signal,
                lot=lot,
                price=entry,
                sl=sl,
                tp=tp,
                deviation=self.settings.execution.deviation,
                comment=f"goldbot:{decision.strategy}",
            )
            result = self.executor.place_order(request)
            self.guardrails.register_entry(now, self.settings.symbol, decision.signal.value)

            row = {
                "timestamp": now.isoformat(),
                "strategy": decision.strategy,
                "regime": regime,
                "signal": decision.signal.value,
                "entry": entry,
                "sl": sl,
                "tp": tp,
                "lot": lot,
                "outcome": "PLACED" if result.ok else "REJECTED",
                "pnl": 0.0,
                "reason": result.message,
            }
            self.journal.record(row)
            self.logger.info("Order attempt", extra={"extra_data": row})
            self.alerter.send(f"{self.settings.symbol} {decision.signal.value} {lot} | {result.message}")
        finally:
            self.data.shutdown()

    def run_loop(self) -> None:
        while True:
            self.run_once()
            time.sleep(self.settings.loop_seconds)
