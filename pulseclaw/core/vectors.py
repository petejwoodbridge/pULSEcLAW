from __future__ import annotations

from typing import Any

import lancedb
import numpy as np
import pyarrow as pa

from pulseclaw.core.config import vector_path

_TABLE = "item_vectors"

_SCHEMA = pa.schema([
    pa.field("item_id", pa.int64()),
    pa.field("topic_id", pa.string()),
    pa.field("embedding", pa.list_(pa.float32())),
    pa.field("published_at", pa.string()),
])


def _db():
    p = vector_path()
    p.mkdir(parents=True, exist_ok=True)
    return lancedb.connect(str(p))


def _table():
    db = _db()
    if _TABLE in db.table_names():
        return db.open_table(_TABLE)
    return db.create_table(_TABLE, schema=_SCHEMA)


def init_vectors() -> None:
    _table()  # triggers creation


def upsert(item_id: int, topic_id: str, embedding: list[float], published_at: str) -> None:
    t = _table()
    t.add([{
        "item_id": int(item_id),
        "topic_id": topic_id,
        "embedding": [float(x) for x in embedding],
        "published_at": published_at,
    }])


def search_similar(embedding: list[float], topic_id: str, k: int = 10) -> list[dict[str, Any]]:
    t = _table()
    q = (
        t.search(embedding)
        .where(f"topic_id = '{topic_id}'")
        .limit(k)
    )
    return [dict(r) for r in q.to_list()]


def fetch_by_ids(item_ids: list[int]) -> list[dict[str, Any]]:
    if not item_ids:
        return []
    t = _table()
    id_list = ",".join(str(int(i)) for i in item_ids)
    return t.search().where(f"item_id IN ({id_list})").limit(len(item_ids) * 2).to_list()


def cosine(a: list[float] | np.ndarray, b: list[float] | np.ndarray) -> float:
    av = np.asarray(a, dtype=np.float32)
    bv = np.asarray(b, dtype=np.float32)
    na, nb = np.linalg.norm(av), np.linalg.norm(bv)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(av, bv) / (na * nb))


def running_centroid(current: list[float] | None, current_n: int,
                     new_vec: list[float], weight: float = 1.0) -> tuple[list[float], int]:
    nv = np.asarray(new_vec, dtype=np.float32)
    if current is None or current_n == 0:
        return nv.tolist(), 1
    cv = np.asarray(current, dtype=np.float32)
    new_n = current_n + weight
    merged = (cv * current_n + nv * weight) / new_n
    return merged.tolist(), int(new_n)


def max_similarity(embedding: list[float], others: list[list[float]]) -> float:
    if not others:
        return 0.0
    sims = [cosine(embedding, o) for o in others]
    return max(sims)
