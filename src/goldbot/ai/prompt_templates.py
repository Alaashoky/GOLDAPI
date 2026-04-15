"""Prompt templates for AI filter."""

from __future__ import annotations

from goldbot.execution.order_models import CandidateSignal


def build_filter_prompt(market_summary: str, signal: CandidateSignal) -> str:
    return (
        "You are a conservative trade risk filter for XAUUSD. "
        "You MUST respond with strict JSON only.\n"
        "Schema: {\"decision\":\"APPROVE|REJECT\",\"reason\":\"...\",\"risk_flags\":[\"...\"]}.\n"
        f"Market summary: {market_summary}\n"
        f"Candidate: strategy={signal.strategy}, signal={signal.signal.value}, confidence={signal.confidence:.2f}, "
        f"rationale={signal.rationale}, sl_basis={signal.sl_basis:.5f}, tp_basis={signal.tp_basis:.5f}\n"
        "If uncertain, reject."
    )
