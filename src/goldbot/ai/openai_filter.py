"""OpenAI-based approval filter with fail-safe behavior."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from dataclasses import dataclass
import json

from goldbot.ai.prompt_templates import build_filter_prompt
from goldbot.execution.order_models import AIDecision, CandidateSignal


@dataclass(slots=True)
class AIFilterResult:
    decision: AIDecision
    reason: str
    risk_flags: list[str]
    raw: str


class OpenAIFilter:
    def __init__(
        self,
        api_key: str,
        model: str,
        enabled: bool = True,
        timeout_seconds: int = 8,
        retries: int = 1,
        fail_behavior: str = "reject",
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.enabled = enabled and bool(api_key)
        self.timeout_seconds = timeout_seconds
        self.retries = retries
        self.fail_behavior = fail_behavior.lower()
        self.client = None
        if self.enabled:
            try:
                from openai import OpenAI

                self.client = OpenAI(api_key=api_key)
            except Exception:
                self.client = None
                self.enabled = False

    def _fallback(self, reason: str) -> AIFilterResult:
        if self.fail_behavior == "approve":
            return AIFilterResult(AIDecision.APPROVE, reason, ["fail_open"], "")
        return AIFilterResult(AIDecision.REJECT, reason, ["fail_safe"], "")

    def _invoke(self, prompt: str) -> str:
        assert self.client is not None
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content or ""

    def analyze(self, market_summary: str, signal: CandidateSignal) -> AIFilterResult:
        if not self.enabled or self.client is None:
            return self._fallback("AI disabled or API key missing")

        prompt = build_filter_prompt(market_summary, signal)
        last_error = ""
        for _ in range(self.retries + 1):
            try:
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(self._invoke, prompt)
                    raw = future.result(timeout=self.timeout_seconds)
                parsed = json.loads(raw)
                decision = str(parsed.get("decision", "REJECT")).upper()
                reason = str(parsed.get("reason", "No reason"))
                risk_flags = [str(v) for v in parsed.get("risk_flags", [])]
                if decision not in {"APPROVE", "REJECT"}:
                    return self._fallback("Invalid AI decision")
                return AIFilterResult(AIDecision(decision), reason, risk_flags, raw)
            except FuturesTimeoutError:
                last_error = "AI timeout"
            except Exception as exc:
                last_error = f"AI error: {exc}"
        return self._fallback(last_error or "AI failure")
