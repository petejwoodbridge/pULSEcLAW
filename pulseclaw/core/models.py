from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RawItem(BaseModel):
    """An item as returned by a source connector, pre-ingest."""

    source: str
    external_id: str
    url: str
    author: str | None = None
    title: str | None = None
    text: str
    media_urls: list[str] = Field(default_factory=list)
    published_at: datetime | None = None
    fetched_at: datetime
    engagement: dict[str, int] = Field(default_factory=dict)
    raw: dict[str, Any] = Field(default_factory=dict)


class Item(BaseModel):
    """Persisted item (row in items table)."""

    id: int
    source: str
    external_id: str
    url: str
    author: str | None
    title: str | None
    text: str
    media_urls: list[str]
    published_at: datetime | None
    fetched_at: datetime
    engagement: dict[str, int]
    content_hash: str


class TopicMatch(BaseModel):
    item_id: int
    topic_id: str
    confidence: float
    subcategory: str | None = None
    reason: str | None = None


class Score(BaseModel):
    item_id: int
    topic_id: str
    relevance: float
    interest_sim: float
    ignore_sim: float
    source_trust: float
    novelty: float
    recency: float
    engagement: float
    rationale: str | None = None


class Cluster(BaseModel):
    id: int
    topic_id: str
    item_ids: list[int]
    centroid_embedding: list[float] | None = None
    event_label: str | None = None
    synthesis: str | None = None
    relevance_max: float
    first_seen: datetime
    last_seen: datetime
    notified_tier: str | None = None
    notified_at: datetime | None = None


class Feedback(BaseModel):
    item_id: int
    kind: str  # "up" | "down" | "more_like" | "less_like" | "mute_author" | "mute_keyword" | "boost_source"
    value: str | None = None  # keyword for mute_keyword; source name for boost_source
    created_at: datetime


class Preference(BaseModel):
    topic_id: str
    interest_centroid: list[float] | None
    ignore_centroid: list[float] | None
    interest_n: int = 0
    ignore_n: int = 0
    muted_authors: list[str] = Field(default_factory=list)
    muted_keywords: list[str] = Field(default_factory=list)
    source_trust: dict[str, float] = Field(default_factory=dict)
    steer_text: str = ""
    updated_at: datetime


class ClassifyResult(BaseModel):
    """Structured output contract for the classify skill."""

    topic_matches: list[dict[str, Any]] = Field(default_factory=list)
    confidence: float = 0.0
    subcategory: str | None = None
    reason: str = ""
