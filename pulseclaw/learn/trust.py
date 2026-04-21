"""v0.2 — per-author / per-subreddit trust learning from aggregated feedback."""
from __future__ import annotations


def recompute_trust(topic_id: str) -> dict[str, float]:  # pragma: no cover
    """Aggregate feedback over last 30 days and compute per-author trust weights."""
    raise NotImplementedError("trust learning — v0.2")
