"""Optional Telegram alerts."""

from __future__ import annotations

from urllib import parse, request


class TelegramAlerter:
    def __init__(self, token: str, chat_id: str) -> None:
        self.token = token
        self.chat_id = chat_id

    @property
    def enabled(self) -> bool:
        return bool(self.token and self.chat_id)

    def send(self, message: str) -> None:
        if not self.enabled:
            return
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = parse.urlencode({"chat_id": self.chat_id, "text": message}).encode("utf-8")
        req = request.Request(url, data=payload, method="POST")
        with request.urlopen(req, timeout=5):
            pass
