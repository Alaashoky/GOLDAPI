"""Technical indicator calculations for AI context."""

from __future__ import annotations

from statistics import mean, pstdev


def ema(values: list[float], period: int) -> list[float]:
    if not values:
        return []
    alpha = 2 / (period + 1)
    out = [values[0]]
    for value in values[1:]:
        out.append(alpha * value + (1 - alpha) * out[-1])
    return out


def rsi(values: list[float], period: int) -> list[float]:
    if len(values) < 2:
        return [50.0] * len(values)
    gains = [0.0]
    losses = [0.0]
    for i in range(1, len(values)):
        delta = values[i] - values[i - 1]
        gains.append(max(delta, 0.0))
        losses.append(max(-delta, 0.0))
    out: list[float] = []
    for i in range(len(values)):
        start = max(0, i - period + 1)
        avg_gain = mean(gains[start : i + 1])
        avg_loss = mean(losses[start : i + 1])
        if avg_loss == 0:
            out.append(100.0)
        else:
            rs = avg_gain / avg_loss
            out.append(100.0 - (100.0 / (1 + rs)))
    return out


def atr(high: list[float], low: list[float], close: list[float], period: int) -> list[float]:
    tr: list[float] = []
    for i in range(len(close)):
        if i == 0:
            tr.append(high[i] - low[i])
        else:
            tr.append(max(high[i] - low[i], abs(high[i] - close[i - 1]), abs(low[i] - close[i - 1])))
    out: list[float] = []
    for i in range(len(tr)):
        start = max(0, i - period + 1)
        out.append(mean(tr[start : i + 1]))
    return out


def bollinger(values: list[float], period: int, std_mult: float) -> tuple[list[float], list[float], list[float]]:
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


def macd(values: list[float], fast: int = 12, slow: int = 26, signal: int = 9) -> tuple[list[float], list[float], list[float]]:
    fast_ema = ema(values, fast)
    slow_ema = ema(values, slow)
    macd_line = [f - s for f, s in zip(fast_ema, slow_ema)]
    signal_line = ema(macd_line, signal)
    histogram = [m - s for m, s in zip(macd_line, signal_line)]
    return macd_line, signal_line, histogram


def stochastic_rsi(values: list[float], rsi_period: int = 14, stoch_period: int = 14) -> list[float]:
    rsi_values = rsi(values, rsi_period)
    out: list[float] = []
    for i in range(len(rsi_values)):
        start = max(0, i - stoch_period + 1)
        window = rsi_values[start : i + 1]
        lo = min(window)
        hi = max(window)
        if hi == lo:
            out.append(0.5)
        else:
            out.append((rsi_values[i] - lo) / (hi - lo))
    return out


def volume_analysis(volumes: list[float], period: int = 20) -> list[float]:
    if not volumes:
        return []
    out: list[float] = []
    for i in range(len(volumes)):
        start = max(0, i - period + 1)
        avg = mean(volumes[start : i + 1])
        out.append((volumes[i] / avg) if avg > 0 else 0.0)
    return out


def pivot_points(high: list[float], low: list[float], close: list[float]) -> tuple[list[float], list[float], list[float]]:
    pivots: list[float] = []
    resistance1: list[float] = []
    support1: list[float] = []
    for i in range(len(close)):
        ref = i - 1 if i > 0 else i
        p = (high[ref] + low[ref] + close[ref]) / 3
        pivots.append(p)
        resistance1.append((2 * p) - low[ref])
        support1.append((2 * p) - high[ref])
    return pivots, resistance1, support1


def append_indicators(
    bars: list[dict],
    ema_fast: int = 20,
    ema_slow: int = 50,
    rsi_period: int = 14,
    atr_period: int = 14,
    bb_period: int = 20,
    bb_std: float = 2.0,
) -> list[dict]:
    closes = [float(b["close"]) for b in bars]
    highs = [float(b["high"]) for b in bars]
    lows = [float(b["low"]) for b in bars]
    volumes = [float(b.get("tick_volume", b.get("real_volume", 0.0))) for b in bars]

    ema_f = ema(closes, ema_fast)
    ema_s = ema(closes, ema_slow)
    rsi_v = rsi(closes, rsi_period)
    atr_v = atr(highs, lows, closes, atr_period)
    bb_mid, bb_upper, bb_lower = bollinger(closes, bb_period, bb_std)
    macd_line, macd_signal, macd_hist = macd(closes)
    stoch_rsi_v = stochastic_rsi(closes, rsi_period=rsi_period)
    vol_ratio = volume_analysis(volumes)
    pivots, r1, s1 = pivot_points(highs, lows, closes)

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
                "macd": macd_line[i],
                "macd_signal": macd_signal[i],
                "macd_hist": macd_hist[i],
                "stoch_rsi": stoch_rsi_v[i],
                "volume_ratio": vol_ratio[i],
                "pivot": pivots[i],
                "pivot_r1": r1[i],
                "pivot_s1": s1[i],
            }
        )
        out.append(enriched)
    return out
