from __future__ import annotations

import os
import tomllib
from functools import lru_cache
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pydantic import BaseModel, Field


ROOT = Path(__file__).resolve().parents[2]
CONFIGS = ROOT / "configs"
TOPICS_DIR = CONFIGS / "topics"


class ServerCfg(BaseModel):
    host: str = "127.0.0.1"
    port: int = 7878


class SchedulerCfg(BaseModel):
    reddit_interval: int = 15
    rss_interval: int = 30
    hackernews_interval: int = 20
    pipeline_interval: int = 10


class PipelineCfg(BaseModel):
    classify_threshold: float = 0.55
    relevance_threshold: float = 0.45
    dedupe_days: int = 14
    dedupe_similarity: float = 0.92
    cluster_window_hours: int = 48


class ScoringCfg(BaseModel):
    w_interest: float = 0.45
    w_ignore: float = 0.15
    w_source_trust: float = 0.1
    w_novelty: float = 0.15
    w_recency: float = 0.1
    w_engagement: float = 0.05


class TierRealtime(BaseModel):
    relevance_min: float = 0.85
    engagement_velocity_z: float = 2.0
    cooldown_hours: int = 6


class TierHourly(BaseModel):
    relevance_min: float = 0.7
    max_items: int = 15


class TierDaily(BaseModel):
    send_at_local: str = "08:00"
    top_n: int = 10


class TierWeekly(BaseModel):
    send_at_local: str = "Sunday 18:00"


class NotifyCfg(BaseModel):
    realtime: TierRealtime = Field(default_factory=TierRealtime)
    hourly: TierHourly = Field(default_factory=TierHourly)
    daily: TierDaily = Field(default_factory=TierDaily)
    weekly: TierWeekly = Field(default_factory=TierWeekly)


class QuietHoursCfg(BaseModel):
    start: str = "22:00"
    end: str = "07:00"


class TopicsCfg(BaseModel):
    active: list[str] = Field(default_factory=lambda: ["creative_ai"])


class Settings(BaseModel):
    server: ServerCfg = Field(default_factory=ServerCfg)
    scheduler: SchedulerCfg = Field(default_factory=SchedulerCfg)
    pipeline: PipelineCfg = Field(default_factory=PipelineCfg)
    scoring: ScoringCfg = Field(default_factory=ScoringCfg)
    notify: NotifyCfg = Field(default_factory=NotifyCfg)
    quiet_hours: QuietHoursCfg = Field(default_factory=QuietHoursCfg)
    topics: TopicsCfg = Field(default_factory=TopicsCfg)


def _load_toml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("rb") as f:
        return tomllib.load(f)


def _coerce_notify(raw: dict[str, Any]) -> dict[str, Any]:
    """pulseclaw.toml uses [notify.tiers.X]; pydantic expects flat NotifyCfg."""
    n = raw.get("notify", {})
    tiers = n.get("tiers", {})
    return {
        "realtime": tiers.get("realtime", {}),
        "hourly": tiers.get("hourly", {}),
        "daily": tiers.get("daily", {}),
        "weekly": tiers.get("weekly", {}),
    }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    load_dotenv(ROOT / ".env", override=False)
    raw = _load_toml(CONFIGS / "pulseclaw.toml")
    raw["notify"] = _coerce_notify(raw)
    return Settings.model_validate(raw)


@lru_cache(maxsize=1)
def get_models() -> dict[str, Any]:
    return _load_toml(CONFIGS / "models.toml")


def load_topic(topic_id: str) -> dict[str, Any]:
    path = TOPICS_DIR / f"{topic_id}.toml"
    if not path.exists():
        raise FileNotFoundError(f"Topic config not found: {path}")
    return _load_toml(path)


def env(name: str, default: str | None = None) -> str | None:
    load_dotenv(ROOT / ".env", override=False)
    return os.environ.get(name, default)


def db_path() -> Path:
    return Path(env("PULSECLAW_DB_PATH", "./data/pulseclaw.sqlite"))


def vector_path() -> Path:
    return Path(env("PULSECLAW_VECTOR_PATH", "./data/lancedb"))
