"""Pluggable news filter provider interface."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class NewsRiskResult:
    blocked: bool
    reason: str


class NewsFilterProvider:
    def should_block(self, symbol: str) -> NewsRiskResult:
        return NewsRiskResult(blocked=False, reason="No provider configured")
