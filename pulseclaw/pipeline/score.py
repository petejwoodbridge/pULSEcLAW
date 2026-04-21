from __future__ import annotations

import logging
import math
from datetime import timedelta

from pulseclaw.core import db, vectors
from pulseclaw.core.clock import now
from pulseclaw.core.config import get_settings
from pulseclaw.core.models import Item

log = logging.getLogger(__name__)


def _recency(published_iso: str | None) -> float:
    if not published_iso:
        return 0.3
    from datetime import datetime
    pub = datetime.fromisoformat(published_iso)
    age_h = (now() - pub).total_seconds() / 3600
    # half-life 24h
    return math.exp(-age_h / 24)


def _engagement_norm(source: str, eng: dict) -> float:
    if source == "reddit":
        ups = eng.get("ups", 0)
        comments = eng.get("num_comments", 0)
        return min(1.0, (ups + 3 * comments) / 500)
    if source == "hackernews":
        points = eng.get("points", 0)
        comments = eng.get("num_comments", 0)
        return min(1.0, (points + 3 * comments) / 300)
    return 0.2


def _novelty(item_id: int, topic_id: str, embedding: list[float] | None) -> float:
    if not embedding:
        return 0.5
    hits = vectors.search_similar(embedding, topic_id, k=10)
    others = [h["embedding"] for h in hits if h.get("item_id") != item_id]
    if not others:
        return 1.0
    max_sim = vectors.max_similarity(embedding, others)
    return 1.0 - max_sim  # very similar → low novelty


def _source_trust(topic_id: str, source: str, author: str | None) -> float:
    prefs = db.get_preferences(topic_id)
    if not prefs:
        return 0.5
    trust = prefs.get("source_trust", {})
    # Author-specific trust beats source-level
    if author and f"{source}:{author}" in trust:
        return float(trust[f"{source}:{author}"])
    if source in trust:
        return float(trust[source])
    return 0.5


def score_one(item: Item, topic_id: str) -> dict:
    prefs = db.get_preferences(topic_id) or {}
    interest = prefs.get("interest_centroid")
    ignore = prefs.get("ignore_centroid")

    hits = vectors.fetch_by_ids([item.id])
    embedding = hits[0]["embedding"] if hits else None

    interest_sim = vectors.cosine(embedding, interest) if (embedding and interest) else 0.5
    ignore_sim = vectors.cosine(embedding, ignore) if (embedding and ignore) else 0.0

    trust = _source_trust(topic_id, item.source, item.author)
    novelty = _novelty(item.id, topic_id, embedding) if embedding else 0.5
    published_iso = item.published_at.isoformat() if item.published_at else None
    recency = _recency(published_iso)
    engagement = _engagement_norm(item.source, item.engagement)

    w = get_settings().scoring
    relevance = (
        w.w_interest * interest_sim
        - w.w_ignore * ignore_sim
        + w.w_source_trust * trust
        + w.w_novelty * novelty
        + w.w_recency * recency
        + w.w_engagement * engagement
    )
    # clamp
    relevance = max(0.0, min(1.0, relevance))

    return {
        "item_id": item.id,
        "topic_id": topic_id,
        "relevance": relevance,
        "interest_sim": interest_sim,
        "ignore_sim": ignore_sim,
        "source_trust": trust,
        "novelty": novelty,
        "recency": recency,
        "engagement": engagement,
    }


def run(topic_id: str, limit: int = 500) -> int:
    threshold = get_settings().pipeline.classify_threshold
    items = db.items_needing_score(topic_id, threshold, limit=limit)
    for item in items:
        try:
            s = score_one(item, topic_id)
            db.save_score(s)
        except Exception as e:
            log.warning("score failed for item %s: %s", item.id, e)
    return len(items)
