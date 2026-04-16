"""Prompt builders for AI market analysis and hybrid trade filtering."""

from __future__ import annotations

import json

FILTER_SYSTEM_PROMPT = (
    "You are an expert XAUUSD trade filter specializing in Smart Money Concepts (SMC) and Liquidity Sweep setups. "
    "You are running in PAPER MODE — no real money is at risk. Your job is to evaluate trade signals and decide "
    "APPROVE or REJECT.\n\n"
    "IMPORTANT GUIDELINES:\n"
    "1. You are in PAPER MODE — be more willing to approve trades for learning and data collection. "
    "Only reject if the setup is clearly invalid or dangerous.\n"
    "2. If trade history is empty or has no wins, that is NORMAL for a new bot — do NOT use this as a reason to reject.\n"
    "3. Focus on the QUALITY of the liquidity sweep: Was there a clear sweep beyond a swing high/low? "
    "Did price reject back? Is there a confirmation candle?\n"
    "4. News impact should add caution but NOT automatically reject. High impact news means tighter SL, not no trade.\n"
    "5. Conflicting timeframe trends are acceptable for liquidity sweeps — sweeps often happen AGAINST the higher timeframe trend.\n"
    "6. A good liquidity sweep setup should be APPROVED even with some risk factors.\n\n"
    "You MUST respond with ONLY a valid JSON object, no markdown, no explanation, no code fences. "
    "JSON schema: "
    '{"decision":"APPROVE|REJECT","confidence":0-100,"reasoning":"...",'
    '"news_impact":"high|medium|low|none","risk_factors":["..."],'
    '"suggested_sl":number|null,"suggested_tp":number|null}'
)
SYSTEM_PROMPT = FILTER_SYSTEM_PROMPT

MARKET_ANALYSIS_SYSTEM_PROMPT = (
    "You are a professional XAUUSD market analyst and risk-aware intraday trader. "
    "Analyze market context step-by-step in this order: trend, market structure, indicators, news, then decision. "
    "Never omit risk controls. If data quality is weak, return HOLD. "
    "You MUST respond with ONLY a valid JSON object, no markdown, no explanation, no code fences. "
    "JSON schema: "
    '{"trend":"bullish|bearish|neutral","support_levels":[number],"resistance_levels":[number],'
    '"risk_factors":[string],"news_impact":"high|medium|low|none","confidence":0-100,'
    '"action":"BUY|SELL|HOLD","entry":number|null,"sl":number|null,"tp":number|null,"reasoning":string}'
)


def build_market_analysis_prompt(
    symbol: str,
    timeframes: dict[str, dict],
    news: list[dict],
    trade_history: list[dict],
    performance_summary: dict,
) -> str:
    payload = {
        "symbol": symbol,
        "timeframes": {
            tf: {
                "trend": frame.get("trend"),
                "latest_indicators": frame.get("candles", [])[-1] if frame.get("candles") else {},
                "candles": frame.get("candles", [])[-50:],
            }
            for tf, frame in timeframes.items()
        },
        "news": news,
        "recent_trade_history": trade_history,
        "performance_summary": performance_summary,
    }
    return (
        "Provide structured market analysis for XAUUSD based on this JSON context. "
        "Think internally step-by-step and return only the final JSON schema.\n"
        f"CONTEXT_JSON={json.dumps(payload, ensure_ascii=False)}"
    )


def _summarize_bars(candles: list[dict], count: int = 100) -> dict:
    """Compute summary stats from recent candles for richer AI filter context."""
    recent = candles[-count:] if len(candles) >= count else candles
    if not recent:
        return {}

    highs = [float(c["high"]) for c in recent]
    lows = [float(c["low"]) for c in recent]
    closes = [float(c["close"]) for c in recent]
    swing_high = max(highs)
    swing_low = min(lows)
    move = swing_high - swing_low
    last = recent[-1]
    price_position_pct = 0.0 if move <= 0 else ((float(last["close"]) - swing_low) / move) * 100

    bullish_candles = sum(1 for c in recent if float(c["close"]) > float(c["open"]))
    bearish_candles = len(recent) - bullish_candles
    summary = {
        "bars_analyzed": len(recent),
        "swing_high": round(swing_high, 2),
        "swing_low": round(swing_low, 2),
        "range": round(move, 2),
        "current_price": round(float(last["close"]), 2),
        "price_position_pct": round(price_position_pct, 1),
        "bullish_candles": bullish_candles,
        "bearish_candles": bearish_candles,
        "bullish_ratio_pct": round(bullish_candles / len(recent) * 100, 1),
    }

    if move > 0:
        summary["fib_236"] = round(swing_high - move * 0.236, 2)
        summary["fib_382"] = round(swing_high - move * 0.382, 2)
        summary["fib_500"] = round(swing_high - move * 0.5, 2)
        summary["fib_618"] = round(swing_high - move * 0.618, 2)
        summary["fib_786"] = round(swing_high - move * 0.786, 2)

    for key in [
        "ema_fast",
        "ema_slow",
        "rsi",
        "atr",
        "macd",
        "macd_signal",
        "macd_hist",
        "bb_upper",
        "bb_mid",
        "bb_lower",
        "stoch_rsi",
        "pivot",
        "pivot_r1",
        "pivot_s1",
    ]:
        val = last.get(key)
        if val is not None:
            summary[key] = round(float(val), 4)

    if summary.get("ema_fast") and summary.get("ema_slow"):
        if summary["ema_fast"] > summary["ema_slow"]:
            summary["trend"] = "bullish"
        elif summary["ema_fast"] < summary["ema_slow"]:
            summary["trend"] = "bearish"
        else:
            summary["trend"] = "neutral"

    return summary


def build_filter_prompt(
    symbol: str,
    candidate: dict,
    timeframes: dict[str, dict],
    news: list[dict],
    trade_history: list[dict],
    performance_summary: dict,
) -> str:
    """Build prompt for AI to evaluate a strategy signal."""
    strategy_signals = candidate.get("all_strategy_signals", [])
    strategy_consensus: dict[str, int | bool | list[dict]] | None = None
    consensus_note = "No strategy consensus available."
    if strategy_signals:
        buy_count = sum(1 for s in strategy_signals if s.get("signal") == "BUY")
        sell_count = sum(1 for s in strategy_signals if s.get("signal") == "SELL")
        hold_count = sum(1 for s in strategy_signals if s.get("signal") == "HOLD")
        single_strategy_mode = len(strategy_signals) == 1
        strategy_consensus = {
            "buy_count": buy_count,
            "sell_count": sell_count,
            "hold_count": hold_count,
            "conflicting": buy_count > 0 and sell_count > 0,
            "mode": "single_strategy" if single_strategy_mode else "multi_strategy",
            "signals": strategy_signals,
        }
        if single_strategy_mode:
            consensus_note = "Single strategy mode — only Liquidity Sweep strategy is active."
        else:
            consensus_note = "Multi-strategy mode — consider consensus and conflicts across strategy signals."

    market_context = {}
    for tf, frame in timeframes.items():
        candles = frame.get("candles", [])
        recent_candles = candles[-10:] if len(candles) >= 10 else candles
        market_context[tf] = {
            "trend": frame.get("trend"),
            "summary": _summarize_bars(candles, count=100),
            "recent_candles": [
                {
                    "time": c.get("time"),
                    "open": round(float(c["open"]), 2),
                    "high": round(float(c["high"]), 2),
                    "low": round(float(c["low"]), 2),
                    "close": round(float(c["close"]), 2),
                    "rsi": round(float(c.get("rsi", 50)), 2),
                    "ema_fast": round(float(c.get("ema_fast", 0)), 2),
                    "ema_slow": round(float(c.get("ema_slow", 0)), 2),
                    "macd_hist": round(float(c.get("macd_hist", 0)), 4),
                }
                for c in recent_candles
            ],
        }

    payload = {
        "symbol": symbol,
        "mode": "PAPER",
        "mode_note": "Paper mode — no real money. Approve more freely for learning.",
        "strategy_signal": candidate,
        "strategy_consensus": strategy_consensus,
        "strategy_consensus_note": consensus_note,
        "market_context": market_context,
        "news": news,
        "recent_trade_history": trade_history,
        "performance_summary": performance_summary,
    }
    if not trade_history:
        payload["trade_history_note"] = "This is a new bot with no trade history yet. Do not penalize for this."
    return (
        f"A trading strategy generated the following signal for {symbol}. "
        "Evaluate whether to APPROVE or REJECT this trade. "
        "You have the last 10 candles per timeframe plus a statistical summary of the last 100 candles "
        "including Fibonacci levels, swing high/low, trend direction, and key indicators. "
        "This is PAPER MODE, so prioritize learning/data collection and reject only clearly invalid setups. "
        "Focus primarily on liquidity sweep quality (clear sweep, rejection, and confirmation). "
        "News should increase caution but should not be an automatic blocker.\n"
        f"SIGNAL_CONTEXT={json.dumps(payload, ensure_ascii=False)}"
    )
