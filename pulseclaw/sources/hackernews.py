from __future__ import annotations

import logging
from datetime import UTC, datetime

import httpx

from pulseclaw.core.clock import now
from pulseclaw.core.models import RawItem
from pulseclaw.sources.base import Source

log = logging.getLogger(__name__)

ALGOLIA = "https://hn.algolia.com/api/v1/search"


class HackerNewsSource(Source):
    name = "hackernews"

    def auth_check(self) -> tuple[bool, str]:
        return (True, "no auth required")

    def fetch(self, topic_cfg: dict) -> list[RawItem]:
        keywords = topic_cfg.get("seeds", {}).get("hackernews", {}).get("keywords", [])
        if not keywords:
            return []
        out: list[RawItem] = []
        fetched = now()
        with httpx.Client(timeout=20.0) as c:
            for kw in keywords:
                try:
                    resp = c.get(ALGOLIA, params={
                        "query": kw,
                        "tags": "story",
                        "hitsPerPage": 20,
                    })
                    resp.raise_for_status()
                    for hit in resp.json().get("hits", []):
                        title = hit.get("title") or hit.get("story_title") or ""
                        text = hit.get("story_text") or title
                        url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit['objectID']}"
                        ts = hit.get("created_at_i")
                        published = datetime.fromtimestamp(ts, tz=UTC) if ts else None
                        out.append(RawItem(
                            source=self.name,
                            external_id=str(hit["objectID"]),
                            url=url,
                            author=hit.get("author"),
                            title=title,
                            text=text,
                            media_urls=[],
                            published_at=published,
                            fetched_at=fetched,
                            engagement={
                                "points": int(hit.get("points") or 0),
                                "num_comments": int(hit.get("num_comments") or 0),
                            },
                            raw={"keyword": kw},
                        ))
                except Exception as e:
                    log.warning("hn fetch failed for %r: %s", kw, e)
        return out
