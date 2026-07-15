from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta

from celery import Celery
from celery.schedules import crontab

from app.core import config
from app.db.session import SessionLocal
from app.services.analytics import rebuild_daily_metrics

ANALYTICS_QUEUE = "analytics"
ANALYTICS_REBUILD_TASK = "analytics_worker.rebuild_daily_metrics"
RECENT_METRIC_DAYS = 2

celery_app = Celery(
    "atlas_analytics_worker",
    broker=config.celery_broker_url(),
    backend=config.celery_result_backend(),
)
celery_app.conf.update(
    task_default_queue=ANALYTICS_QUEUE,
    task_routes={ANALYTICS_REBUILD_TASK: {"queue": ANALYTICS_QUEUE}},
    beat_schedule={
        "rebuild-recent-daily-analytics": {
            "task": ANALYTICS_REBUILD_TASK,
            "schedule": crontab(hour=0, minute=5),
        }
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
