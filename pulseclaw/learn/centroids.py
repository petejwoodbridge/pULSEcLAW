from __future__ import annotations

import logging

from pulseclaw.core import db, vectors

log = logging.getLogger(__name__)


def _embedding_for(item_id: int) -> list[float] | None:
    hits = vectors.fetch_by_ids([item_id])
    if not hits:
        return None
    return hits[0]["embedding"]


def apply_feedback(topic_id: str, item_id: int, kind: str) -> None:
    """Update interest / ignore centroids in response to a thumbs signal."""
    vec = _embedding_for(item_id)
    if vec is None:
        log.warning("no embedding for item %s; skipping centroid update", item_id)
        return
    prefs = db.get_preferences(topic_id) or {}
    interest = prefs.get("interest_centroid")
    ignore = prefs.get("ignore_centroid")
    interest_n = prefs.get("interest_n", 0)
    ignore_n = prefs.get("ignore_n", 0)

    weight = {"up": 1.0, "down": 1.0, "more_like": 1.5, "less_like": 1.5}.get(kind, 0.0)
    if weight == 0.0:
        return

    if kind in ("up", "more_like"):
        interest, interest_n = vectors.running_centroid(interest, interest_n, vec, weight)
    else:
        ignore, ignore_n = vectors.running_centroid(ignore, ignore_n, vec, weight)

    db.upsert_preferences(
        topic_id,
        interest_centroid=interest,
        ignore_centroid=ignore,
        interest_n=interest_n,
        ignore_n=ignore_n,
    )


def boost_source(topic_id: str, source_or_author: str, delta: float = 0.1) -> None:
    prefs = db.get_preferences(topic_id) or {}
    trust = prefs.get("source_trust", {})
    current = float(trust.get(source_or_author, 0.5))
    trust[source_or_author] = min(2.0, current + delta)
    db.upsert_preferences(topic_id, source_trust=trust)


def mute_author(topic_id: str, author: str) -> None:
    prefs = db.get_preferences(topic_id) or {}
    authors = list(set(prefs.get("muted_authors", []) + [author]))
    trust = prefs.get("source_trust", {})
    trust[author] = 0.0
    db.upsert_preferences(topic_id, muted_authors=authors, source_trust=trust)


def mute_keyword(topic_id: str, keyword: str) -> None:
    prefs = db.get_preferences(topic_id) or {}
    kws = list(set(prefs.get("muted_keywords", []) + [keyword.strip().lower()]))
    db.upsert_preferences(topic_id, muted_keywords=kws)


def set_steer_text(topic_id: str, text: str) -> None:
    db.upsert_preferences(topic_id, steer_text=text.strip())
