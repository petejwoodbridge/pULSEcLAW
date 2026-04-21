from __future__ import annotations

import logging
from datetime import UTC, datetime

import praw

from pulseclaw.core.clock import now
from pulseclaw.core.config import env
from pulseclaw.core.models import RawItem
from pulseclaw.sources.base import Source

log = logging.getLogger(__name__)


class RedditSource(Source):
    name = "reddit"

    def _client(self) -> praw.Reddit:
        return praw.Reddit(
            client_id=env("REDDIT_CLIENT_ID"),
            client_secret=env("REDDIT_CLIENT_SECRET"),
            user_agent=env("REDDIT_USER_AGENT", "pulseclaw/0.1"),
            username=env("REDDIT_USERNAME"),
            password=env("REDDIT_PASSWORD"),
            check_for_async=False,
        )

    def auth_check(self) -> tuple[bool, str]:
        try:
            r = self._client()
            me = r.user.me()
            return (True, f"authed as {me.name}" if me else "read-only")
        except Exception as e:
            return (False, str(e))

    def fetch(self, topic_cfg: dict) -> list[RawItem]:
        subs = topic_cfg.get("seeds", {}).get("reddit", {}).get("subreddits", [])
        if not subs:
            return []
        r = self._client()
        out: list[RawItem] = []
        fetched = now()
        for sub in subs:
            try:
                for post in r.subreddit(sub).hot(limit=25):
                    text = post.selftext or post.title
                    out.append(RawItem(
                        source=self.name,
                        external_id=post.id,
                        url=f"https://reddit.com{post.permalink}",
                        author=str(post.author) if post.author else None,
                        title=post.title,
                        text=text,
                        media_urls=[post.url] if getattr(post, "url", None) else [],
                        published_at=datetime.fromtimestamp(post.created_utc, tz=UTC),
                        fetched_at=fetched,
                        engagement={
                            "ups": int(getattr(post, "ups", 0)),
                            "num_comments": int(getattr(post, "num_comments", 0)),
                        },
                        raw={"subreddit": sub, "over_18": bool(getattr(post, "over_18", False))},
                    ))
            except Exception as e:
                log.warning("reddit fetch failed for r/%s: %s", sub, e)
        return out
