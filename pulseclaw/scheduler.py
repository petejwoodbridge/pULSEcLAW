from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from pulseclaw.core.config import get_settings
from pulseclaw.notify import dispatcher
from pulseclaw.pipeline import run as pipeline_run

log = logging.getLogger(__name__)


def build_scheduler(active_topics: list[str]) -> BackgroundScheduler:
    s = get_settings()
    sched = BackgroundScheduler(timezone="UTC")

    for topic in active_topics:
        sched.add_job(
            pipeline_run.fetch_and_ingest,
            trigger=IntervalTrigger(minutes=s.scheduler.rss_interval),
            args=["rss", topic],
            id=f"fetch_rss_{topic}",
            replace_existing=True,
            misfire_grace_time=300,
        )
        sched.add_job(
            pipeline_run.fetch_and_ingest,
            trigger=IntervalTrigger(minutes=s.scheduler.hackernews_interval),
            args=["hackernews", topic],
            id=f"fetch_hn_{topic}",
            replace_existing=True,
            misfire_grace_time=300,
        )
        sched.add_job(
            pipeline_run.fetch_and_ingest,
            trigger=IntervalTrigger(minutes=s.scheduler.reddit_interval),
            args=["reddit", topic],
            id=f"fetch_reddit_{topic}",
            replace_existing=True,
            misfire_grace_time=300,
        )
        sched.add_job(
            pipeline_run.pipeline_only,
            trigger=IntervalTrigger(minutes=s.scheduler.pipeline_interval),
            args=[topic],
            id=f"pipeline_{topic}",
            replace_existing=True,
            misfire_grace_time=300,
        )
        sched.add_job(
            dispatcher.dispatch_realtime,
            trigger=IntervalTrigger(minutes=5),
            args=[topic],
            id=f"realtime_{topic}",
            replace_existing=True,
        )

        hh, mm = _parse_hhmm(s.notify.daily.send_at_local)
        sched.add_job(
            dispatcher.dispatch_daily,
            trigger=CronTrigger(hour=hh, minute=mm),
            args=[topic],
            id=f"daily_{topic}",
            replace_existing=True,
        )

    return sched


def _parse_hhmm(s: str) -> tuple[int, int]:
    try:
        hh, mm = s.split(":")
        return int(hh), int(mm)
    except Exception:
        return 8, 0
