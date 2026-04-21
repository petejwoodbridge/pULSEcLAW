from __future__ import annotations

from pulseclaw.core.models import RawItem
from pulseclaw.sources.base import Source


class TwitterSource(Source):
    """
    v0.2 stub.

    Plan:
      - Primary: official X API v2 via TWITTER_BEARER_TOKEN. Home timeline + lists + searches.
      - Fallback: twitterapi.io via TWITTERAPI_IO_KEY. Same endpoints, different shape.
      - snscrape and public Nitter are broken as of 2026. Do NOT add them.
      - Rate limit: 900 req / 15 min on official; check quota headers on twitterapi.io.
    """

    name = "twitter"

    def auth_check(self) -> tuple[bool, str]:
        return (False, "TODO v0.2 — not implemented")

    def fetch(self, topic_cfg: dict) -> list[RawItem]:
        return []
