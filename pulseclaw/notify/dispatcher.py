from __future__ import annotations

import logging
from datetime import datetime, time, timedelta

from pulseclaw.core import db
from pulseclaw.core.clock import now
from pulseclaw.core.config import get_settings
from pulseclaw.core.db import connection
from pulseclaw.llm.client import chat
from pulseclaw.llm.prompts import load_rendered
from pulseclaw.notify.desktop import DesktopNotifier
from pulseclaw.notify.ntfy import NtfyNotifier

log = logging.getLogger(__name__)


def _in_quiet_hours() -> bool:
    qh = get_settings().quiet_hours
    try:
        start = time.fromisoformat(qh.start)
        end = time.fromisoformat(qh.end)
    except ValueError:
        return False
    current = now().time()
    if start < end:
        return start <= current < end
    return current >= start or current < end


def _send_all(title: str, body: str, url: str | None = None) -> bool:
    sent = False
    for notifier in (NtfyNotifier(), DesktopNotifier()):
        if notifier.send(title, body, url):
            sent = True
    return sent


def dispatch_realtime(topic_id: str) -> int:
    """Push high-signal clusters that haven't been notified yet."""
    if _in_quiet_hours():
        return 0
    tier = get_settings().notify.realtime
    clusters = db.clusters_awaiting_notification(tier.relevance_min)
    sent = 0
    for c in clusters:
        # cooldown: skip if we already pushed any realtime in last N hours on same topic
        if _recent_realtime(topic_id, tier.cooldown_hours):
            break
        label = c.get("event_label") or "Pulse alert"
        body = (c.get("synthesis") or "").strip()
        url = _primary_link_for_cluster(c["id"])
        if _send_all(label, body[:800], url):
            db.mark_cluster_notified(c["id"], "realtime")
            _log_notification(c["id"], "realtime", "ntfy+desktop", ok=True)
            sent += 1
    return sent


def dispatch_daily(topic_id: str) -> int:
    """08:00 daily digest — top N clusters of last 24h."""
    settings = get_settings().notify.daily
    since_dt = now() - timedelta(hours=24)
    with connection() as c:
        rows = c.execute(
            """
            SELECT * FROM clusters
            WHERE topic_id = ?
              AND synthesis IS NOT NULL
              AND last_seen >= ?
            ORDER BY relevance_max DESC
            LIMIT ?
            """,
            (topic_id, since_dt.isoformat(), settings.top_n),
        ).fetchall()
        clusters = [dict(r) for r in rows]
    if not clusters:
        return 0

    digest = _render_digest(clusters, kind="daily")
    _send_all("PulseClaw daily", digest[:800])
    for cl in clusters:
        if not cl.get("notified_tier"):
            db.mark_cluster_notified(cl["id"], "daily")
        _log_notification(cl["id"], "daily", "ntfy+desktop", ok=True)
    return len(clusters)


def _render_digest(clusters: list[dict], kind: str) -> str:
    entries = []
    for c in clusters:
        label = c.get("event_label") or ""
        synth = (c.get("synthesis") or "").strip()
        entries.append(f"— {label}\n{synth}")
    items_block = "\n\n".join(entries)
    try:
        _, body = load_rendered("generate_daily_digest", items_block=items_block, n=len(clusters))
        return chat("daily_digest", [{"role": "user", "content": body}])
    except Exception as e:
        log.warning("digest LLM render failed, falling back to raw: %s", e)
        return items_block


def _primary_link_for_cluster(cluster_id: int) -> str | None:
    with connection() as c:
        r = c.execute(
            """
            SELECT i.url FROM cluster_items ci
            JOIN items i ON i.id = ci.item_id
            ORDER BY i.published_at DESC LIMIT 1
            """,
        ).fetchone()
        return r["url"] if r else None


def _recent_realtime(topic_id: str, cooldown_hours: int) -> bool:
    cutoff = (now() - timedelta(hours=cooldown_hours)).isoformat()
    with connection() as c:
        r = c.execute(
            """
            SELECT 1 FROM notifications_sent ns
            JOIN clusters cl ON cl.id = ns.cluster_id
            WHERE ns.tier = 'realtime' AND ns.sent_at >= ? AND cl.topic_id = ?
            LIMIT 1
            """,
            (cutoff, topic_id),
        ).fetchone()
        return r is not None


def _log_notification(cluster_id: int, tier: str, transport: str, ok: bool,
                      error: str | None = None) -> None:
    with connection() as c:
        c.execute(
            """
            INSERT INTO notifications_sent (cluster_id, tier, sent_at, transport, ok, error)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (cluster_id, tier, now().isoformat(), transport, int(ok), error),
        )
