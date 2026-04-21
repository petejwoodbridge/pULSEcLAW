from __future__ import annotations

import logging
from datetime import UTC, datetime
from time import mktime

import feedparser

from pulseclaw.core.clock import now
from pulseclaw.core.models import RawItem
from pulseclaw.sources.base import Source

log = logging.getLogger(__name__)


class RSSSource(Source):
    name = "rss"

    def auth_check(self) -> tuple[bool, str]:
        return (True, "no auth required")

    def fetch(self, topic_cfg: dict) -> list[RawItem]:
        feeds = topic_cfg.get("seeds", {}).get("rss", {}).get("feeds", [])
        out: list[RawItem] = []
        fetched = now()
        for url in feeds:
            try:
                parsed = feedparser.parse(url)
                if parsed.bozo and not parsed.entries:
                    log.warning("rss parse failed: %s", url)
                    continue
                for entry in parsed.entries[:30]:
                    published = None
                    if getattr(entry, "published_parsed", None):
                        published = datetime.fromtimestamp(mktime(entry.published_parsed), tz=UTC)
                    elif getattr(entry, "updated_parsed", None):
                        published = datetime.fromtimestamp(mktime(entry.updated_parsed), tz=UTC)
                    link = getattr(entry, "link", url)
                    ext = getattr(entry, "id", link)
                    summary = getattr(entry, "summary", "") or ""
                    title = getattr(entry, "title", "")
                    out.append(RawItem(
                        source=self.name,
                        external_id=ext,
                        url=link,
                        author=getattr(entry, "author", None),
                        title=title,
                        text=f"{title}\n\n{summary}",
                        media_urls=[],
                        published_at=published,
                        fetched_at=fetched,
                        engagement={},
                        raw={"feed": url},
                    ))
            except Exception as e:
                log.warning("rss fetch failed for %s: %s", url, e)
        return out
