from __future__ import annotations

import logging
from dataclasses import asdict, dataclass

from pulseclaw.core.config import get_settings, load_topic
from pulseclaw.pipeline import classify, cluster, ingest, score, synthesize
from pulseclaw.sources import get_source

log = logging.getLogger(__name__)


@dataclass
class CycleReport:
    topic_id: str
    ingested: dict[str, dict]
    classified: int
    scored: int
    clustered: int
    synthesized: int


def fetch_and_ingest(source_name: str, topic_id: str) -> dict:
    topic_cfg = load_topic(topic_id)
    src = get_source(source_name)
    raw = src.fetch(topic_cfg)
    rep = ingest.ingest_raw(raw, topic_id)
    return asdict(rep)


def full_cycle(topic_id: str, sources: list[str] | None = None) -> CycleReport:
    sources = sources or ["rss", "hackernews", "reddit"]
    ingested: dict[str, dict] = {}
    for s in sources:
        try:
            ingested[s] = fetch_and_ingest(s, topic_id)
        except Exception as e:
            log.warning("fetch failed for %s: %s", s, e)
            ingested[s] = {"error": str(e)}

    c = classify.run(topic_id)
    s = score.run(topic_id)
    k = cluster.run(topic_id)
    y = synthesize.run(topic_id)

    return CycleReport(
        topic_id=topic_id,
        ingested=ingested,
        classified=c,
        scored=s,
        clustered=k,
        synthesized=y,
    )


def pipeline_only(topic_id: str) -> CycleReport:
    """Run classify → score → cluster → synthesize without fetching."""
    c = classify.run(topic_id)
    s = score.run(topic_id)
    k = cluster.run(topic_id)
    y = synthesize.run(topic_id)
    return CycleReport(topic_id=topic_id, ingested={}, classified=c, scored=s,
                       clustered=k, synthesized=y)
