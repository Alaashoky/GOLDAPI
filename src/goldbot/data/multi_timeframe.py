"""Multi-timeframe market data aggregation."""

from __future__ import annotations

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
    output: dict[str, dict] = {}
    for timeframe in timeframes:
        raw = adapter.get_rates(symbol, timeframe, bars)
        enriched = append_indicators(raw)
        trend = _trend_from_last_bar(enriched[-1])
        output[timeframe] = {
            "timeframe": timeframe,
            "trend": trend,
            "candles": enriched,
        }
    return output
