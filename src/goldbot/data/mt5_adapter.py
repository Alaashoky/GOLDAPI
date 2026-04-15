"""MetaTrader5 data adapter."""

from __future__ import annotations

from typing import Any


def _to_python(val: Any) -> Any:
    """Convert numpy-like scalars (e.g., int64/float64 via `.item()`) for JSON safety."""
    if hasattr(val, "item"):
        return val.item()
    return val


class MT5DataAdapter:
    def __init__(self, login: int | None, password: str, server: str) -> None:
        self.login = login
        self.password = password
        self.server = server
        self.mt5 = None

    def initialize(self) -> None:
        try:
            import MetaTrader5 as mt5  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("MetaTrader5 package is not available") from exc
        self.mt5 = mt5
        ok = mt5.initialize(login=self.login, password=self.password, server=self.server)
        if not ok:
            raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")

    def shutdown(self) -> None:
        if self.mt5 is not None:
            self.mt5.shutdown()

    def ensure_symbol(self, symbol: str) -> None:
        assert self.mt5 is not None
        info = self.mt5.symbol_info(symbol)
        if info is None:
            raise RuntimeError(f"Symbol not found: {symbol}")
        if not info.visible and not self.mt5.symbol_select(symbol, True):
            raise RuntimeError(f"Failed to make symbol visible: {symbol}")

    def get_rates(self, symbol: str, timeframe: str, bars: int) -> list[dict]:
        assert self.mt5 is not None
        tf = getattr(self.mt5, f"TIMEFRAME_{timeframe}", None)
        if tf is None:
            raise ValueError(f"Unsupported timeframe: {timeframe}")
        rates = self.mt5.copy_rates_from_pos(symbol, tf, 0, bars)
        if rates is None or len(rates) == 0:
            raise RuntimeError("No bars received from MT5")
        dtype = getattr(rates, "dtype", None)
        names = getattr(dtype, "names", None) if dtype is not None else None
        if names:
            return [{k: _to_python(v) for k, v in zip(names, row)} for row in rates]
        return [{k: _to_python(v) for k, v in dict(row).items()} for row in rates]

    def get_tick(self, symbol: str) -> Any:
        assert self.mt5 is not None
        tick = self.mt5.symbol_info_tick(symbol)
        if tick is None:
            raise RuntimeError("No tick data")
        return tick

    def account_info(self) -> Any:
        assert self.mt5 is not None
        return self.mt5.account_info()

    def open_positions(self, symbol: str | None = None) -> list[Any]:
        assert self.mt5 is not None
        if symbol:
            return self.mt5.positions_get(symbol=symbol) or []
        return self.mt5.positions_get() or []
