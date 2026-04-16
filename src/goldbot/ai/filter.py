"""AI trade filter for hybrid strategy + AI flow."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from dataclasses import dataclass
import json
import logging

from goldbot.ai.analyzer import _extract_json
from goldbot.ai.prompts import SYSTEM_PROMPT, build_filter_prompt
from goldbot.execution.models import CandidateSignal


@dataclass(slots=True)
class FilterResult:
    decision: str
    confidence: int
    reasoning: str
    risk_factors: list[str]
    news_impact: str
    suggested_sl: float | None
    suggested_tp: float | None
    raw: str = ""


class AITradeFilter:
    """AI evaluates strategy signals and approves/rejects execution."""

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

    def _fallback(self, reason: str) -> FilterResult:
        return FilterResult(
            decision="REJECT",
            confidence=0,
            reasoning=reason,
            risk_factors=[reason],
            news_impact="none",
            suggested_sl=None,
            suggested_tp=None,
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
            logging.getLogger("goldbot").warning("AI trade filter returned no choices")
            return ""
        message = response.choices[0].message
        return str(getattr(message, "content", "") or "")

    def evaluate(
        self,
        symbol: str,
        candidate_signal: CandidateSignal | dict,
        timeframes: dict[str, dict],
        news: list[dict],
        trade_history: list[dict],
        performance_summary: dict,
    ) -> FilterResult:
        if not self.enabled:
            return self._fallback("AI unavailable")

        if isinstance(candidate_signal, dict):
            candidate_dict = dict(candidate_signal)
        else:
            candidate_dict = {
                "strategy": candidate_signal.strategy,
                "signal": candidate_signal.signal.value,
                "confidence": int(max(0, min(100, round(candidate_signal.confidence * 100)))),
                "rationale": candidate_signal.rationale,
                "sl_basis": candidate_signal.sl_basis,
                "tp_basis": candidate_signal.tp_basis,
            }

        prompt = build_filter_prompt(
            symbol=symbol,
            candidate=candidate_dict,
            timeframes=timeframes,
            news=news,
            trade_history=trade_history,
            performance_summary=performance_summary,
        )

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
                decision = str(parsed.get("decision", "REJECT")).upper()
                if decision not in {"APPROVE", "REJECT"}:
                    decision = "REJECT"

                confidence = int(max(0, min(100, int(parsed.get("confidence", 0)))))
                sl = parsed.get("suggested_sl_adjustment")
                tp = parsed.get("suggested_tp_adjustment")
                return FilterResult(
                    decision=decision,
                    confidence=confidence,
                    reasoning=str(parsed.get("reasoning", "No reasoning provided")),
                    risk_factors=[str(x) for x in parsed.get("risk_factors", [])],
                    news_impact=str(parsed.get("news_impact", "none")),
                    suggested_sl=float(sl) if sl is not None else None,
                    suggested_tp=float(tp) if tp is not None else None,
                    raw=raw,
                )
            except (json.JSONDecodeError, ValueError) as exc:
                last_error = f"AI JSON parse error: {exc}"
            except FuturesTimeoutError:
                last_error = "AI timeout"
            except Exception as exc:
                last_error = str(exc)

        return self._fallback(last_error)
