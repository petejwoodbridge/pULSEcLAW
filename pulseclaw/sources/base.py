from __future__ import annotations

from abc import ABC, abstractmethod

from pulseclaw.core.models import RawItem


class Source(ABC):
    """Common interface every connector implements."""

    name: str

    @abstractmethod
    def fetch(self, topic_cfg: dict) -> list[RawItem]:
        """Fetch current items from the source. Never writes to DB."""

    @abstractmethod
    def auth_check(self) -> tuple[bool, str]:
        """Return (ok, detail)."""

    def health(self) -> dict:
        ok, detail = self.auth_check()
        return {"source": self.name, "ok": ok, "detail": detail}
