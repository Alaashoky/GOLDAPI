"""Prompt builders for AI market analysis and hybrid trade filtering."""

from __future__ import annotations

import json

SYSTEM_PROMPT = (
    "You are a professional XAUUSD trade evaluator and risk manager. "
    "A trading strategy has generated a signal. Your job is to EVALUATE whether this signal "
    "should be APPROVED or REJECTED based on: market context, news impact, trade history, "
    "and overall risk assessment. "
    "You are NOT generating the signal — you are judging its quality. "
    "You MUST respond with ONLY a valid JSON object, no markdown, no explanation, no code fences. "
    "JSON schema: "
    '{"decision":"APPROVE|REJECT",'
    '"confidence":0-100,'
    '"reasoning":string,'
    '"risk_factors":[string],'
    '"news_impact":"high|medium|low|none",'
    '"suggested_sl_adjustment":number|null,'
    '"suggested_tp_adjustment":number|null}'
)

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


def build_filter_prompt(
    symbol: str,
    candidate: dict,
    timeframes: dict[str, dict],
    news: list[dict],
    trade_history: list[dict],
    performance_summary: dict,
) -> str:
    """Build prompt for AI to evaluate a strategy signal."""
    payload = {
        "symbol": symbol,
        "strategy_signal": candidate,
        "market_context": {
            tf: {
                "trend": frame.get("trend"),
                "latest": frame.get("candles", [])[-1] if frame.get("candles") else {},
            }
            for tf, frame in timeframes.items()
        },
        "news": news,
        "recent_trade_history": trade_history,
        "performance_summary": performance_summary,
    }
    return (
        f"A trading strategy generated the following signal for {symbol}. "
        "Evaluate whether to APPROVE or REJECT this trade. "
        "Consider: trend alignment across timeframes, news impact, recent trade performance, "
        "and risk factors. Only APPROVE if the setup is solid.\n"
        f"SIGNAL_CONTEXT={json.dumps(payload, ensure_ascii=False)}"
    )
