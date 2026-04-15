"""MT5 order execution wrapper."""

from __future__ import annotations

from datetime import datetime, timezone

from goldbot.execution.order_models import OrderRequest, OrderResult, Signal


class MT5Executor:
    def __init__(self, enabled: bool, deviation: int = 20, magic: int = 20260415) -> None:
        self.enabled = enabled
        self.deviation = deviation
        self.magic = magic
        self.mt5 = None

    def bind_mt5(self, mt5_module) -> None:
        self.mt5 = mt5_module

    def _validate_symbol(self, symbol: str) -> None:
        assert self.mt5 is not None
        info = self.mt5.symbol_info(symbol)
        if info is None:
            raise RuntimeError(f"Symbol not available: {symbol}")
        if not info.visible and not self.mt5.symbol_select(symbol, True):
            raise RuntimeError(f"Cannot select symbol: {symbol}")

    def place_order(self, request: OrderRequest) -> OrderResult:
        if request.sl <= 0 or request.tp <= 0:
            return OrderResult(False, "SL/TP are required")

        if not self.enabled:
            fake_ticket = int(datetime.now(tz=timezone.utc).timestamp())
            return OrderResult(True, "Paper mode order accepted", ticket=fake_ticket)

        if self.mt5 is None:
            return OrderResult(False, "MT5 module not bound")

        try:
            self._validate_symbol(request.symbol)
        except Exception as exc:
            return OrderResult(False, str(exc))

        order_type = self.mt5.ORDER_TYPE_BUY if request.signal == Signal.BUY else self.mt5.ORDER_TYPE_SELL
        trade_req = {
            "action": self.mt5.TRADE_ACTION_DEAL,
            "symbol": request.symbol,
            "volume": request.lot,
            "type": order_type,
            "price": request.price,
            "sl": request.sl,
            "tp": request.tp,
            "deviation": request.deviation,
            "magic": self.magic,
            "comment": request.comment,
            "type_time": self.mt5.ORDER_TIME_GTC,
            "type_filling": self.mt5.ORDER_FILLING_IOC,
        }
        result = self.mt5.order_send(trade_req)
        if result is None:
            return OrderResult(False, "order_send returned None")
        if result.retcode != self.mt5.TRADE_RETCODE_DONE:
            return OrderResult(False, f"MT5 order failed: retcode={result.retcode}", retcode=result.retcode)
        return OrderResult(True, "Order executed", ticket=result.order, retcode=result.retcode)
