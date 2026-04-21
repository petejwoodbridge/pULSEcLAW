from __future__ import annotations

from pulseclaw.core.models import RawItem
from pulseclaw.sources.base import Source


class GitHubSource(Source):
    """
    v0.2 stub.

    Plan:
      - Trending repos in topic (via HTML scrape of github.com/trending + language filter).
      - Releases from a watchlist of repos via GitHub REST API v3. Use GITHUB_TOKEN.
      - Authenticated rate limit: 5000 req/hour.
    """

    name = "github"

    def auth_check(self) -> tuple[bool, str]:
        return (False, "TODO v0.2 — not implemented")

    def fetch(self, topic_cfg: dict) -> list[RawItem]:
        return []
