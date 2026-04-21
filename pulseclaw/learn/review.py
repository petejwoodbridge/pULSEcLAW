"""v0.2 — weekly preference review generation + accept/reject apply."""
from __future__ import annotations


def generate_review(topic_id: str) -> dict:  # pragma: no cover
    """Summarize learned adjustments since last review. Returns proposal list."""
    raise NotImplementedError("preference review — v0.2")


def apply_review(topic_id: str, decisions: dict) -> None:  # pragma: no cover
    raise NotImplementedError("preference review — v0.2")
