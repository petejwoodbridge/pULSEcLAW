from __future__ import annotations

import logging
from typing import Any

from pulseclaw.core import db
from pulseclaw.core.config import get_settings, load_topic
from pulseclaw.core.models import Item
from pulseclaw.llm.client import chat_json
from pulseclaw.llm.prompts import load_rendered

log = logging.getLogger(__name__)

SKILL_NAME = "classify_item"


def _skill_version() -> str:
    from pulseclaw.llm.prompts import load_skill
    meta, _ = load_skill(SKILL_NAME)
    return meta.get("version", "v1")


def classify_one(item: Item, topic_id: str) -> dict[str, Any]:
    topic_cfg = load_topic(topic_id)
    topic_def = topic_cfg["topic"]
    _, body = load_rendered(
        SKILL_NAME,
        topic_id=topic_id,
        topic_name=topic_def["name"],
        topic_description=topic_def["description"].strip(),
        title=item.title or "",
        text=item.text[:2500],
        source=item.source,
        author=item.author or "",
    )
    out = chat_json("classify", [{"role": "user", "content": body}])
    return out


def run(topic_id: str, limit: int = 200) -> int:
    """Classify un-classified items for topic. Returns count processed."""
    version = _skill_version()
    threshold = get_settings().pipeline.classify_threshold
    prefs = db.get_preferences(topic_id) or {}
    muted_kw = [k.lower() for k in prefs.get("muted_keywords", [])]
    muted_authors = set(prefs.get("muted_authors", []))

    items = db.items_needing_classify(topic_id, version, limit=limit)
    processed = 0
    for item in items:
        # Hard filters first
        if item.author and item.author in muted_authors:
            db.save_topic_match(item.id, topic_id, 0.0, None, "muted_author", version)
            processed += 1
            continue
        haystack = f"{item.title or ''} {item.text}".lower()
        if any(kw in haystack for kw in muted_kw):
            db.save_topic_match(item.id, topic_id, 0.0, None, "muted_keyword", version)
            processed += 1
            continue

        try:
            result = classify_one(item, topic_id)
            confidence = float(result.get("confidence", 0.0))
            subcategory = result.get("subcategory")
            reason = result.get("reason", "")[:500]
            if confidence >= threshold:
                db.save_topic_match(item.id, topic_id, confidence, subcategory, reason, version)
            else:
                db.save_topic_match(item.id, topic_id, confidence, subcategory,
                                    f"below_threshold: {reason}", version)
            processed += 1
        except Exception as e:
            log.warning("classify failed for item %s: %s", item.id, e)
    return processed
