from pulseclaw.sources.base import Source
from pulseclaw.sources.hackernews import HackerNewsSource
from pulseclaw.sources.reddit import RedditSource
from pulseclaw.sources.rss import RSSSource

REGISTRY: dict[str, type[Source]] = {
    "reddit": RedditSource,
    "rss": RSSSource,
    "hackernews": HackerNewsSource,
}


def get_source(name: str) -> Source:
    cls = REGISTRY.get(name)
    if not cls:
        raise ValueError(f"Unknown source: {name}. Available: {list(REGISTRY)}")
    return cls()
