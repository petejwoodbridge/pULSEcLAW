"""v0.2 — SMTP digest email."""
from __future__ import annotations

from pulseclaw.notify.base import Notifier


class EmailNotifier(Notifier):  # pragma: no cover
    name = "email"

    def send(self, title: str, body: str, url: str | None = None) -> bool:
        raise NotImplementedError("email — v0.2")
