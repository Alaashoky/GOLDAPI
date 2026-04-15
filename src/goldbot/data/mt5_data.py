"""MT5 adapters and indicator helpers."""

from __future__ import annotations

from statistics import mean, pstdev


class MT5DataAdapter:
    def __init__(self, login: int | None, password: str, server: str) -> None:
        self.login = login
        self.password = password
        self.server = server
        self.mt5 = None

    def initialize(self) -> None:
        try:
            import MetaTrader5 as mt5  # type: ignore
        except Exception as exc:  # pragma: no cover
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
        return [dict(r) for r in rates]

    def get_tick(self, symbol: str):
        assert self.mt5 is not None
        tick = self.mt5.symbol_info_tick(symbol)
        if tick is None:
            raise RuntimeError("No tick data")
        return tick

    def account_info(self):
        assert self.mt5 is not None
        return self.mt5.account_info()

    def open_positions(self, symbol: str | None = None):
        assert self.mt5 is not None
        if symbol:
            return self.mt5.positions_get(symbol=symbol) or []
        return self.mt5.positions_get() or []


def _ema(values: list[float], period: int) -> list[float]:
    if not values:
        return []
    alpha = 2 / (period + 1)
    output = [values[0]]
    for value in values[1:]:
        output.append(alpha * value + (1 - alpha) * output[-1])
    return output


def _rsi(values: list[float], period: int) -> list[float]:
    if len(values) < 2:
        return [50.0] * len(values)
    gains = [0.0]
    losses = [0.0]
    for i in range(1, len(values)):
        delta = values[i] - values[i - 1]
        gains.append(max(delta, 0.0))
        losses.append(max(-delta, 0.0))
    rsi_values: list[float] = []
    for i in range(len(values)):
        start = max(0, i - period + 1)
        avg_gain = mean(gains[start : i + 1])
        avg_loss = mean(losses[start : i + 1])
        if avg_loss == 0:
            rsi_values.append(100.0)
        else:
            rs = avg_gain / avg_loss
            rsi_values.append(100.0 - (100.0 / (1 + rs)))
    return rsi_values


def _atr(high: list[float], low: list[float], close: list[float], period: int) -> list[float]:
    tr: list[float] = []
    for i in range(len(close)):
        if i == 0:
            tr.append(high[i] - low[i])
            continue
        tr.append(max(high[i] - low[i], abs(high[i] - close[i - 1]), abs(low[i] - close[i - 1])))
    atr_values: list[float] = []
    for i in range(len(tr)):
        start = max(0, i - period + 1)
        atr_values.append(mean(tr[start : i + 1]))
    return atr_values


def _bollinger(values: list[float], period: int, std_mult: float) -> tuple[list[float], list[float], list[float]]:
    mid: list[float] = []
    upper: list[float] = []
    lower: list[float] = []
    for i in range(len(values)):
        start = max(0, i - period + 1)
        sample = values[start : i + 1]
        m = mean(sample)
        sd = pstdev(sample) if len(sample) > 1 else 0.0
        mid.append(m)
        upper.append(m + sd * std_mult)
        lower.append(m - sd * std_mult)
    return mid, upper, lower


def append_indicators(
    bars: list[dict],
    ema_fast: int,
    ema_slow: int,
    rsi_period: int,
    atr_period: int,
    bb_period: int,
    bb_std: float,
) -> list[dict]:
    closes = [float(b["close"]) for b in bars]
    highs = [float(b["high"]) for b in bars]
    lows = [float(b["low"]) for b in bars]
    ema_f = _ema(closes, ema_fast)
    ema_s = _ema(closes, ema_slow)
    rsi_v = _rsi(closes, rsi_period)
    atr_v = _atr(highs, lows, closes, atr_period)
    bb_mid, bb_upper, bb_lower = _bollinger(closes, bb_period, bb_std)
    out: list[dict] = []
    for i, bar in enumerate(bars):
        enriched = dict(bar)
        enriched.update(
            {
                "ema_fast": ema_f[i],
                "ema_slow": ema_s[i],
                "rsi": rsi_v[i],
                "atr": atr_v[i],
                "bb_mid": bb_mid[i],
                "bb_upper": bb_upper[i],
                "bb_lower": bb_lower[i],
            }
        )
        out.append(enriched)
    return out
