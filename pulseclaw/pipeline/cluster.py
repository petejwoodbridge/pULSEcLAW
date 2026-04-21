from __future__ import annotations

import logging
from datetime import timedelta

import hdbscan
import numpy as np

from pulseclaw.core import db, vectors
from pulseclaw.core.clock import now, to_iso
from pulseclaw.core.config import get_settings

log = logging.getLogger(__name__)


def _recent_items(topic_id: str, hours: int, min_relevance: float) -> list[dict]:
    since = to_iso(now() - timedelta(hours=hours))
    return db.top_scored_items(topic_id, since, min_relevance, limit=300)


def run(topic_id: str) -> int:
    """Cluster recent high-relevance items. Creates new clusters for un-clustered ones."""
    settings = get_settings()
    window = settings.pipeline.cluster_window_hours
    min_rel = settings.pipeline.relevance_threshold

    rows = _recent_items(topic_id, window, min_rel)
    if len(rows) < 2:
        return 0

    ids = [r["id"] for r in rows]
    hits = vectors.fetch_by_ids(ids)
    id_to_vec = {h["item_id"]: h["embedding"] for h in hits}
    ordered_ids = [i for i in ids if i in id_to_vec]
    if len(ordered_ids) < 2:
        return 0

    matrix = np.array([id_to_vec[i] for i in ordered_ids], dtype=np.float32)
    clusterer = hdbscan.HDBSCAN(
        metric="euclidean",
        min_cluster_size=2,
        min_samples=1,
        cluster_selection_epsilon=0.3,
    )
    labels = clusterer.fit_predict(matrix)

    # Group ids by label; -1 is noise (skip — stays as singleton in reading queue)
    groups: dict[int, list[int]] = {}
    for iid, lbl in zip(ordered_ids, labels, strict=True):
        if lbl == -1:
            continue
        groups.setdefault(int(lbl), []).append(iid)

    # Filter to groups with no existing cluster
    created = 0
    for _, item_ids in groups.items():
        if not _any_already_clustered(item_ids):
            rel = max(r["relevance"] for r in rows if r["id"] in item_ids)
            published = [r["fetched_at"] for r in rows if r["id"] in item_ids]
            db.create_cluster(
                topic_id=topic_id,
                item_ids=item_ids,
                relevance_max=rel,
                first_seen_iso=min(published),
                last_seen_iso=max(published),
            )
            created += 1
    return created


def _any_already_clustered(item_ids: list[int]) -> bool:
    from pulseclaw.core.db import connection
    q = ",".join("?" * len(item_ids))
    with connection() as c:
        r = c.execute(
            f"SELECT 1 FROM cluster_items WHERE item_id IN ({q}) LIMIT 1",
            item_ids,
        ).fetchone()
        return r is not None
