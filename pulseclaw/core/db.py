from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from pulseclaw.core.clock import now, to_iso
from pulseclaw.core.config import db_path
from pulseclaw.core.models import Feedback, Item, RawItem

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source          TEXT NOT NULL,
    external_id     TEXT NOT NULL,
    url             TEXT NOT NULL,
    author          TEXT,
    title           TEXT,
    text            TEXT NOT NULL,
    media_urls      TEXT NOT NULL DEFAULT '[]',
    published_at    TEXT,
    fetched_at      TEXT NOT NULL,
    engagement      TEXT NOT NULL DEFAULT '{}',
    content_hash    TEXT NOT NULL,
    UNIQUE(source, external_id)
);
CREATE INDEX IF NOT EXISTS ix_items_hash ON items(content_hash);
CREATE INDEX IF NOT EXISTS ix_items_fetched ON items(fetched_at);

CREATE TABLE IF NOT EXISTS topic_matches (
    item_id         INTEGER NOT NULL,
    topic_id        TEXT NOT NULL,
    confidence      REAL NOT NULL,
    subcategory     TEXT,
    reason          TEXT,
    skill_version   TEXT NOT NULL,
    PRIMARY KEY (item_id, topic_id, skill_version),
    FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS scores (
    item_id         INTEGER NOT NULL,
    topic_id        TEXT NOT NULL,
    relevance       REAL NOT NULL,
    interest_sim    REAL NOT NULL,
    ignore_sim      REAL NOT NULL,
    source_trust    REAL NOT NULL,
    novelty         REAL NOT NULL,
    recency         REAL NOT NULL,
    engagement      REAL NOT NULL,
    rationale       TEXT,
    computed_at     TEXT NOT NULL,
    PRIMARY KEY (item_id, topic_id),
    FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS clusters (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id        TEXT NOT NULL,
    event_label     TEXT,
    synthesis       TEXT,
    relevance_max   REAL NOT NULL DEFAULT 0.0,
    first_seen      TEXT NOT NULL,
    last_seen       TEXT NOT NULL,
    notified_tier   TEXT,
    notified_at     TEXT
);

CREATE TABLE IF NOT EXISTS cluster_items (
    cluster_id      INTEGER NOT NULL,
    item_id         INTEGER NOT NULL,
    PRIMARY KEY (cluster_id, item_id),
    FOREIGN KEY (cluster_id) REFERENCES clusters(id) ON DELETE CASCADE,
    FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS feedback (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id         INTEGER,
    kind            TEXT NOT NULL,
    value           TEXT,
    created_at      TEXT NOT NULL,
    FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS preferences (
    topic_id        TEXT PRIMARY KEY,
    interest_centroid TEXT,
    ignore_centroid   TEXT,
    interest_n      INTEGER NOT NULL DEFAULT 0,
    ignore_n        INTEGER NOT NULL DEFAULT 0,
    muted_authors   TEXT NOT NULL DEFAULT '[]',
    muted_keywords  TEXT NOT NULL DEFAULT '[]',
    source_trust    TEXT NOT NULL DEFAULT '{}',
    steer_text      TEXT NOT NULL DEFAULT '',
    updated_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS source_state (
    source          TEXT PRIMARY KEY,
    paused          INTEGER NOT NULL DEFAULT 0,
    last_fetch_at   TEXT,
    last_ok         INTEGER NOT NULL DEFAULT 1,
    last_error      TEXT,
    cursor          TEXT
);

CREATE TABLE IF NOT EXISTS notifications_sent (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    cluster_id      INTEGER,
    tier            TEXT NOT NULL,
    sent_at         TEXT NOT NULL,
    transport       TEXT NOT NULL,
    ok              INTEGER NOT NULL DEFAULT 1,
    error           TEXT
);

CREATE TABLE IF NOT EXISTS click_events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id         INTEGER NOT NULL,
    occurred_at     TEXT NOT NULL,
    dwell_ms        INTEGER,
    FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE
);
"""


def _conn(path: Path | None = None) -> sqlite3.Connection:
    p = path or db_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(p))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


@contextmanager
def connection(path: Path | None = None):
    c = _conn(path)
    try:
        yield c
        c.commit()
    except Exception:
        c.rollback()
        raise
    finally:
        c.close()


def init_db(path: Path | None = None) -> None:
    with connection(path) as c:
        c.executescript(SCHEMA)


# --- items ---


def content_hash(text: str) -> str:
    return hashlib.sha256(text.strip().lower().encode("utf-8")).hexdigest()


def insert_raw(raw: RawItem) -> int | None:
    """Insert if new; return item_id or None if duplicate."""
    h = content_hash(raw.text or raw.url)
    with connection() as c:
        try:
            cur = c.execute(
                """
                INSERT INTO items
                    (source, external_id, url, author, title, text, media_urls,
                     published_at, fetched_at, engagement, content_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    raw.source,
                    raw.external_id,
                    raw.url,
                    raw.author,
                    raw.title,
                    raw.text,
                    json.dumps(raw.media_urls),
                    to_iso(raw.published_at) if raw.published_at else None,
                    to_iso(raw.fetched_at),
                    json.dumps(raw.engagement),
                    h,
                ),
            )
            return cur.lastrowid
        except sqlite3.IntegrityError:
            return None


def _row_to_item(r: sqlite3.Row) -> Item:
    from datetime import datetime

    return Item(
        id=r["id"],
        source=r["source"],
        external_id=r["external_id"],
        url=r["url"],
        author=r["author"],
        title=r["title"],
        text=r["text"],
        media_urls=json.loads(r["media_urls"]),
        published_at=datetime.fromisoformat(r["published_at"]) if r["published_at"] else None,
        fetched_at=datetime.fromisoformat(r["fetched_at"]),
        engagement=json.loads(r["engagement"]),
        content_hash=r["content_hash"],
    )


def get_item(item_id: int) -> Item | None:
    with connection() as c:
        r = c.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
        return _row_to_item(r) if r else None


def items_needing_classify(topic_id: str, skill_version: str, limit: int = 200) -> list[Item]:
    with connection() as c:
        rows = c.execute(
            """
            SELECT i.* FROM items i
            WHERE NOT EXISTS (
                SELECT 1 FROM topic_matches tm
                WHERE tm.item_id = i.id AND tm.topic_id = ? AND tm.skill_version = ?
            )
            ORDER BY i.fetched_at DESC
            LIMIT ?
            """,
            (topic_id, skill_version, limit),
        ).fetchall()
        return [_row_to_item(r) for r in rows]


def items_needing_score(topic_id: str, min_confidence: float, limit: int = 500) -> list[Item]:
    with connection() as c:
        rows = c.execute(
            """
            SELECT i.* FROM items i
            JOIN topic_matches tm ON tm.item_id = i.id
            LEFT JOIN scores s ON s.item_id = i.id AND s.topic_id = tm.topic_id
            WHERE tm.topic_id = ? AND tm.confidence >= ? AND s.item_id IS NULL
            ORDER BY i.fetched_at DESC
            LIMIT ?
            """,
            (topic_id, min_confidence, limit),
        ).fetchall()
        return [_row_to_item(r) for r in rows]


def save_topic_match(item_id: int, topic_id: str, confidence: float,
                     subcategory: str | None, reason: str | None, skill_version: str) -> None:
    with connection() as c:
        c.execute(
            """
            INSERT OR REPLACE INTO topic_matches
                (item_id, topic_id, confidence, subcategory, reason, skill_version)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (item_id, topic_id, confidence, subcategory, reason, skill_version),
        )


def save_score(s: dict[str, Any]) -> None:
    with connection() as c:
        c.execute(
            """
            INSERT OR REPLACE INTO scores
                (item_id, topic_id, relevance, interest_sim, ignore_sim,
                 source_trust, novelty, recency, engagement, rationale, computed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                s["item_id"],
                s["topic_id"],
                s["relevance"],
                s["interest_sim"],
                s["ignore_sim"],
                s["source_trust"],
                s["novelty"],
                s["recency"],
                s["engagement"],
                s.get("rationale"),
                to_iso(now()),
            ),
        )


def top_scored_items(topic_id: str, since_iso: str, min_relevance: float,
                     limit: int = 50) -> list[dict[str, Any]]:
    with connection() as c:
        rows = c.execute(
            """
            SELECT i.*, s.relevance
            FROM items i
            JOIN scores s ON s.item_id = i.id
            WHERE s.topic_id = ?
              AND i.fetched_at >= ?
              AND s.relevance >= ?
            ORDER BY s.relevance DESC
            LIMIT ?
            """,
            (topic_id, since_iso, min_relevance, limit),
        ).fetchall()
        return [dict(r) for r in rows]


# --- feedback ---


def record_feedback(fb: Feedback) -> None:
    with connection() as c:
        c.execute(
            "INSERT INTO feedback (item_id, kind, value, created_at) VALUES (?, ?, ?, ?)",
            (fb.item_id, fb.kind, fb.value, to_iso(fb.created_at)),
        )


def recent_feedback(kind: str | None = None, limit: int = 500) -> list[dict[str, Any]]:
    with connection() as c:
        if kind:
            rows = c.execute(
                "SELECT * FROM feedback WHERE kind = ? ORDER BY id DESC LIMIT ?",
                (kind, limit),
            ).fetchall()
        else:
            rows = c.execute(
                "SELECT * FROM feedback ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]


# --- preferences ---


def get_preferences(topic_id: str) -> dict[str, Any] | None:
    with connection() as c:
        r = c.execute("SELECT * FROM preferences WHERE topic_id = ?", (topic_id,)).fetchone()
        if not r:
            return None
        d = dict(r)
        d["interest_centroid"] = json.loads(d["interest_centroid"]) if d["interest_centroid"] else None
        d["ignore_centroid"] = json.loads(d["ignore_centroid"]) if d["ignore_centroid"] else None
        d["muted_authors"] = json.loads(d["muted_authors"])
        d["muted_keywords"] = json.loads(d["muted_keywords"])
        d["source_trust"] = json.loads(d["source_trust"])
        return d


def upsert_preferences(topic_id: str, **fields: Any) -> None:
    current = get_preferences(topic_id) or {
        "topic_id": topic_id,
        "interest_centroid": None,
        "ignore_centroid": None,
        "interest_n": 0,
        "ignore_n": 0,
        "muted_authors": [],
        "muted_keywords": [],
        "source_trust": {},
        "steer_text": "",
    }
    current.update(fields)
    with connection() as c:
        c.execute(
            """
            INSERT INTO preferences
                (topic_id, interest_centroid, ignore_centroid, interest_n, ignore_n,
                 muted_authors, muted_keywords, source_trust, steer_text, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(topic_id) DO UPDATE SET
                interest_centroid = excluded.interest_centroid,
                ignore_centroid = excluded.ignore_centroid,
                interest_n = excluded.interest_n,
                ignore_n = excluded.ignore_n,
                muted_authors = excluded.muted_authors,
                muted_keywords = excluded.muted_keywords,
                source_trust = excluded.source_trust,
                steer_text = excluded.steer_text,
                updated_at = excluded.updated_at
            """,
            (
                topic_id,
                json.dumps(current["interest_centroid"]) if current["interest_centroid"] else None,
                json.dumps(current["ignore_centroid"]) if current["ignore_centroid"] else None,
                current["interest_n"],
                current["ignore_n"],
                json.dumps(current["muted_authors"]),
                json.dumps(current["muted_keywords"]),
                json.dumps(current["source_trust"]),
                current["steer_text"],
                to_iso(now()),
            ),
        )


# --- clusters ---


def create_cluster(topic_id: str, item_ids: list[int], relevance_max: float,
                   first_seen_iso: str, last_seen_iso: str) -> int:
    with connection() as c:
        cur = c.execute(
            """
            INSERT INTO clusters (topic_id, relevance_max, first_seen, last_seen)
            VALUES (?, ?, ?, ?)
            """,
            (topic_id, relevance_max, first_seen_iso, last_seen_iso),
        )
        cid = cur.lastrowid
        for iid in item_ids:
            c.execute("INSERT INTO cluster_items (cluster_id, item_id) VALUES (?, ?)", (cid, iid))
        return cid


def save_synthesis(cluster_id: int, event_label: str, synthesis: str) -> None:
    with connection() as c:
        c.execute(
            "UPDATE clusters SET event_label = ?, synthesis = ? WHERE id = ?",
            (event_label, synthesis, cluster_id),
        )


def mark_cluster_notified(cluster_id: int, tier: str) -> None:
    with connection() as c:
        c.execute(
            "UPDATE clusters SET notified_tier = ?, notified_at = ? WHERE id = ?",
            (tier, to_iso(now()), cluster_id),
        )


def clusters_awaiting_notification(tier_min_relevance: float) -> list[dict[str, Any]]:
    with connection() as c:
        rows = c.execute(
            """
            SELECT * FROM clusters
            WHERE notified_tier IS NULL
              AND synthesis IS NOT NULL
              AND relevance_max >= ?
            ORDER BY relevance_max DESC
            """,
            (tier_min_relevance,),
        ).fetchall()
        return [dict(r) for r in rows]


# --- source state ---


def set_source_state(source: str, *, paused: bool | None = None, last_ok: bool | None = None,
                     last_error: str | None = None, cursor: str | None = None) -> None:
    with connection() as c:
        c.execute(
            """
            INSERT INTO source_state (source, paused, last_ok, last_error, cursor, last_fetch_at)
            VALUES (?, COALESCE(?, 0), COALESCE(?, 1), ?, ?, ?)
            ON CONFLICT(source) DO UPDATE SET
                paused = COALESCE(excluded.paused, source_state.paused),
                last_ok = COALESCE(excluded.last_ok, source_state.last_ok),
                last_error = excluded.last_error,
                cursor = COALESCE(excluded.cursor, source_state.cursor),
                last_fetch_at = excluded.last_fetch_at
            """,
            (
                source,
                int(paused) if paused is not None else None,
                int(last_ok) if last_ok is not None else None,
                last_error,
                cursor,
                to_iso(now()),
            ),
        )


def get_source_state(source: str) -> dict[str, Any] | None:
    with connection() as c:
        r = c.execute("SELECT * FROM source_state WHERE source = ?", (source,)).fetchone()
        return dict(r) if r else None
