from __future__ import annotations

import logging

import httpx

from pulseclaw.core.config import env
from pulseclaw.notify.base import Notifier

log = logging.getLogger(__name__)


class NtfyNotifier(Notifier):
    name = "ntfy"

    def send(self, title: str, body: str, url: str | None = None) -> bool:
        base = env("NTFY_URL", "http://localhost:8080")
        topic = env("NTFY_TOPIC", "pulseclaw-alerts")
        headers = {"Title": title.encode("utf-8", "ignore").decode("ascii", "ignore")}
        if url:
            headers["Click"] = url
        try:
            r = httpx.post(f"{base}/{topic}", data=body.encode("utf-8"),
                          headers=headers, timeout=10.0)
            r.raise_for_status()
            return True
        except Exception as e:
            log.warning("ntfy send failed: %s", e)
            return False
