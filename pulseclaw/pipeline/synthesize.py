from __future__ import annotations

import json
import logging

from pulseclaw.core import db
from pulseclaw.core.db import connection
from pulseclaw.llm.client import chat_json
from pulseclaw.llm.prompts import load_rendered

log = logging.getLogger(__name__)

SKILL_NAME = "cluster_synthesize"


def _items_for_cluster(cluster_id: int) -> list[dict]:
    with connection() as c:
        rows = c.execute(
            """
            SELECT i.id, i.source, i.title, i.text, i.url, i.author, i.published_at
            FROM cluster_items ci
            JOIN items i ON i.id = ci.item_id
            WHERE ci.cluster_id = ?
            ORDER BY i.published_at DESC
            """,
            (cluster_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def _unsynthesized_clusters(topic_id: str) -> list[dict]:
    with connection() as c:
        rows = c.execute(
            """
            SELECT * FROM clusters
            WHERE topic_id = ? AND synthesis IS NULL
            ORDER BY relevance_max DESC
            """,
            (topic_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def synthesize_cluster(cluster_id: int) -> dict:
    items = _items_for_cluster(cluster_id)
    if not items:
        return {}
    items_block = "\n\n".join(
        f"[{i+1}] ({it['source']}) {it['title'] or ''}\n{it['url']}\n{(it['text'] or '')[:600]}"
        for i, it in enumerate(items)
    )
    _, body = load_rendered(SKILL_NAME, items_block=items_block, n=len(items))
    out = chat_json("synthesize", [{"role": "user", "content": body}])
    event_label = out.get("event_label", "")[:200]
    synthesis = out.get("synthesis", "")[:2000]
    if synthesis:
        db.save_synthesis(cluster_id, event_label, synthesis)
    return out


def run(topic_id: str, limit: int = 20) -> int:
    clusters = _unsynthesized_clusters(topic_id)[:limit]
    for cl in clusters:
        try:
            synthesize_cluster(cl["id"])
        except Exception as e:
            log.warning("synth failed for cluster %s: %s", cl["id"], e)
    return len(clusters)
