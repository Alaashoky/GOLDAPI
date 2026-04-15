"""AI-first market analyzer for XAUUSD."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
import json
import logging

from goldbot.ai.prompts import SYSTEM_PROMPT, build_market_analysis_prompt
from goldbot.execution.models import AIAnalysis, Signal


def _extract_json(raw: str) -> str:
    """Extract JSON from AI response, stripping markdown fences and extra text."""
    text = raw.strip()
    if not text:
        return ""
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]
    return text


class MarketAnalyzer:
    def __init__(self, api_key: str, model: str, timeout_seconds: int = 12, retries: int = 1) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.retries = retries
        self.client = None
        if api_key:
            try:
                from openai import OpenAI

                self.client = OpenAI(api_key=api_key)
            except Exception:
                self.client = None

    @property
    def enabled(self) -> bool:
        return self.client is not None

    def _fallback(self, reason: str) -> AIAnalysis:
        return AIAnalysis(
            trend="neutral",
            support_levels=[],
            resistance_levels=[],
            risk_factors=[reason],
            news_impact="none",
            confidence=0,
            action=Signal.HOLD,
            reasoning=reason,
            raw="",
        )

    def _invoke(self, prompt: str) -> str:
        assert self.client is not None
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        if not response.choices:
            logging.getLogger("goldbot").warning("AI analyzer returned no choices")
            return ""
        message = response.choices[0].message
        return str(getattr(message, "content", "") or "")

    def analyze(
        self,
        symbol: str,
        timeframes: dict[str, dict],
        news: list[dict],
        trade_history: list[dict],
        performance_summary: dict,
    ) -> AIAnalysis:
        if not self.enabled:
            return self._fallback("AI unavailable")

        prompt = build_market_analysis_prompt(symbol, timeframes, news, trade_history, performance_summary)
        last_error = "AI returned invalid response"
        for _ in range(self.retries + 1):
            try:
                with ThreadPoolExecutor(max_workers=1) as pool:
                    raw = pool.submit(self._invoke, prompt).result(timeout=self.timeout_seconds)
                cleaned = _extract_json(raw)
                if not cleaned:
                    last_error = "AI empty response after cleaning"
                    continue
                parsed = json.loads(cleaned)
                action = str(parsed.get("action", "HOLD")).upper()
                signal = Signal(action) if action in {"BUY", "SELL", "HOLD"} else Signal.HOLD
                confidence = int(max(0, min(100, int(parsed.get("confidence", 0)))))
                entry = parsed.get("entry")
                sl = parsed.get("sl")
                tp = parsed.get("tp")
                return AIAnalysis(
                    trend=str(parsed.get("trend", "neutral")),
                    support_levels=[float(x) for x in parsed.get("support_levels", [])],
                    resistance_levels=[float(x) for x in parsed.get("resistance_levels", [])],
                    risk_factors=[str(x) for x in parsed.get("risk_factors", [])],
                    news_impact=str(parsed.get("news_impact", "none")),
                    confidence=confidence,
                    action=signal,
                    reasoning=str(parsed.get("reasoning", "")),
                    entry=float(entry) if entry is not None else None,
                    sl=float(sl) if sl is not None else None,
                    tp=float(tp) if tp is not None else None,
                    raw=raw,
                )
            except (json.JSONDecodeError, ValueError) as exc:
                last_error = f"AI JSON parse error: {exc}"
            except FuturesTimeoutError:
                last_error = "AI timeout"
            except Exception as exc:
                last_error = str(exc)

        return self._fallback(last_error)
