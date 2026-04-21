from __future__ import annotations

import logging
from dataclasses import dataclass

from pulseclaw.core import db
from pulseclaw.core.models import RawItem
from pulseclaw.llm.embed import embed
from pulseclaw.core import vectors

log = logging.getLogger(__name__)


@dataclass
class IngestReport:
    fetched: int
    inserted: int
    deduped: int
    errors: int


def ingest_raw(items: list[RawItem], topic_id: str) -> IngestReport:
    """Persist raw items to SQLite + embed + upsert vector. Idempotent via (source, external_id)."""
    inserted = deduped = errors = 0
    for item in items:
        try:
            iid = db.insert_raw(item)
            if iid is None:
                deduped += 1
                continue
            inserted += 1
            try:
                vec = embed(item.text[:4000])
                pub = item.published_at.isoformat() if item.published_at else ""
                vectors.upsert(iid, topic_id, vec, pub)
            except Exception as e:
                log.warning("embed failed for item %s: %s", iid, e)
                errors += 1
        except Exception as e:
            log.exception("ingest failed for %s/%s: %s", item.source, item.external_id, e)
            errors += 1
    return IngestReport(fetched=len(items), inserted=inserted, deduped=deduped, errors=errors)
