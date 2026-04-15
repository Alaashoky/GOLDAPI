"""Economic news feed integration with graceful fallback."""

from __future__ import annotations

from datetime import datetime, timezone

import requests

GOLD_KEYWORDS = {
    "gold",
    "xauusd",
    "usd",
    "dollar",
    "fed",
    "federal reserve",
    "fomc",
    "cpi",
    "inflation",
    "nfp",
    "interest",
    "rate",
    "treasury",
    "geopolitical",
}

HIGH_IMPACT_KEYWORDS = {"fed", "fomc", "cpi", "nfp", "interest", "rate", "inflation"}
MEDIUM_IMPACT_KEYWORDS = {"usd", "dollar", "treasury", "geopolitical"}


class NewsFeed:
    def __init__(self, api_key: str, timeout_seconds: int = 8) -> None:
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def _impact(self, text: str) -> str:
        lowered = text.lower()
        if any(k in lowered for k in HIGH_IMPACT_KEYWORDS):
            return "high"
        if any(k in lowered for k in MEDIUM_IMPACT_KEYWORDS):
            return "medium"
        return "low"

    def fetch(self, limit: int = 20) -> list[dict]:
        if not self.enabled:
            return []

        try:
            now = datetime.now(tz=timezone.utc)
            frm = now.replace(hour=0, minute=0, second=0, microsecond=0).strftime("%Y-%m-%d")
            to = now.strftime("%Y-%m-%d")
            response = requests.get(
                "https://finnhub.io/api/v1/news",
                params={"category": "general", "from": frm, "to": to, "token": self.api_key},
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            items = response.json() or []
        except Exception:
            return []

        filtered: list[dict] = []
        for item in items:
            title = str(item.get("headline") or "")
            summary = str(item.get("summary") or "")
            text = f"{title} {summary}".lower()
            if not any(keyword in text for keyword in GOLD_KEYWORDS):
                continue
            filtered.append(
                {
                    "headline": title,
                    "summary": summary,
                    "source": str(item.get("source") or "finnhub"),
                    "url": str(item.get("url") or ""),
                    "datetime": int(item.get("datetime") or 0),
                    "impact": self._impact(text),
                }
            )
            if len(filtered) >= limit:
                break
        return filtered
