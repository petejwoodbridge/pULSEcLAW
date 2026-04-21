from __future__ import annotations

from pulseclaw.core.models import RawItem
from pulseclaw.sources.base import Source


class LinkedInSource(Source):
    """
    v0.2 stub.

    LinkedIn has no usable public API for this use case. The planned approach is:
      - Use a pasted authenticated `li_at` session cookie (LINKEDIN_LI_AT).
      - Warn the operator clearly — this can get the account suspended.
      - Pull from feed, followed people/companies, and hashtag searches.
      - Rate-limit aggressively. Do not scrape >1 req / 3s.
    """

    name = "linkedin"

    def auth_check(self) -> tuple[bool, str]:
        return (False, "TODO v0.2 — not implemented")

    def fetch(self, topic_cfg: dict) -> list[RawItem]:
        return []
