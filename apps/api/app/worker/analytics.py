from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timedelta, timezone

from celery import Celery
from celery.schedules import crontab

from app.core import config
from app.db.session import SessionLocal
from app.services.analytics import rebuild_daily_metrics
from app.services.telemetry_retention import DEFAULT_BATCH_SIZE, RetentionSummary, purge_playback_events, retention_cutoff

ANALYTICS_QUEUE = "analytics"
ANALYTICS_REBUILD_TASK = "analytics_worker.rebuild_daily_metrics"
TELEMETRY_PURGE_TASK = "analytics_worker.purge_telemetry"
RECENT_METRIC_DAYS = 2

celery_app = Celery(
    "atlas_analytics_worker",
    broker=config.celery_broker_url(),
    backend=config.celery_result_backend(),
)
celery_app.conf.update(
    task_default_queue=ANALYTICS_QUEUE,
    task_routes={
        ANALYTICS_REBUILD_TASK: {"queue": ANALYTICS_QUEUE},
        TELEMETRY_PURGE_TASK: {"queue": ANALYTICS_QUEUE},
    },
    beat_schedule={
        "rebuild-recent-daily-analytics": {
            "task": ANALYTICS_REBUILD_TASK,
            "schedule": crontab(hour=0, minute=5),
        },
        "purge-raw-playback-telemetry": {
            "task": TELEMETRY_PURGE_TASK,
            "schedule": crontab(hour=0, minute=20),
        },
    },
    timezone="UTC",
)
logger = logging.getLogger(__name__)


@celery_app.task(name=ANALYTICS_REBUILD_TASK, ignore_result=True)
def rebuild_recent_daily_metrics(days: int = RECENT_METRIC_DAYS) -> dict[str, object]:
    return asyncio.run(_rebuild_recent_daily_metrics(days))


async def _rebuild_recent_daily_metrics(days: int) -> dict[str, object]:
    if days < 1:
        raise ValueError("days must be at least 1")
    date_to = date.today()
    date_from = date_to - timedelta(days=days - 1)
    async with SessionLocal() as session:
        result = await rebuild_daily_metrics(session, date_from=date_from, date_to=date_to)
    summary = {
        "date_from": result.date_from.isoformat(),
        "date_to": result.date_to.isoformat(),
        "video_metric_rows": result.video_metric_rows,
        "creator_metric_rows": result.creator_metric_rows,
    }
    logger.info("sector=G stage=analytics_rebuild_complete %s", summary)
    return summary


@celery_app.task(name=TELEMETRY_PURGE_TASK, ignore_result=True)
def purge_raw_playback_events(batch_size: int = DEFAULT_BATCH_SIZE) -> dict[str, object]:
    return asyncio.run(_purge_raw_playback_events(batch_size=batch_size))


async def _purge_raw_playback_events(
    *,
    batch_size: int = DEFAULT_BATCH_SIZE,
    now: datetime | None = None,
) -> dict[str, object]:
    current_now = now or datetime.now(timezone.utc)
    cutoff = retention_cutoff(now=current_now)
    async with SessionLocal() as session:
        result: RetentionSummary = await purge_playback_events(
            session,
            cutoff=cutoff,
            batch_size=batch_size,
            apply=True,
        )
    summary = {
        "status": "applied",
        "cutoff": result.cutoff.isoformat(),
        "batch_size": result.batch_size,
        "eligible_rows": result.eligible_rows,
        "purged_rows": result.purged_rows,
        "batches": result.batches,
    }
    logger.info("sector=G stage=telemetry_retention_complete %s", summary)
    return summary
