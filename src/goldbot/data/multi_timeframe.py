"""Multi-timeframe market data aggregation."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from goldbot.data.indicators import append_indicators
from goldbot.data.mt5_adapter import MT5DataAdapter


def _trend_from_last_bar(bar: dict) -> str:
    close = float(bar.get("close", 0.0))
    ema_fast = float(bar.get("ema_fast", close))
    ema_slow = float(bar.get("ema_slow", close))
    if ema_fast > ema_slow and close >= ema_fast:
        return "bullish"
    if ema_fast < ema_slow and close <= ema_fast:
        return "bearish"
    return "neutral"


def fetch_multi_timeframe_data(
    adapter: MT5DataAdapter,
    symbol: str,
    timeframes: list[str],
    bars: int,
) -> dict[str, dict]:
    def _fetch(tf: str) -> tuple[str, list[dict]]:
        raw = adapter.get_rates(symbol, tf, bars)
        enriched = append_indicators(raw)
        return tf, enriched

    output: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=max(1, len(timeframes))) as pool:
        for timeframe, series in pool.map(_fetch, timeframes):
            output[timeframe] = {
                "timeframe": timeframe,
                "trend": _trend_from_last_bar(series[-1]),
                "candles": series,
            }
    return output
