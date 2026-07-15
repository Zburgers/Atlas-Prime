from __future__ import annotations

import asyncio
import logging

from celery import Celery

from app.core import config
from app.db.session import SessionLocal
from app.services.search_index import rebuild_public_video_index

SEARCH_QUEUE = "search"
SEARCH_REINDEX_TASK = "search_worker.rebuild_public_video_index"

celery_app = Celery("atlas_search_worker", broker=config.celery_broker_url(), backend=config.celery_result_backend())
celery_app.conf.update(task_default_queue=SEARCH_QUEUE, task_routes={SEARCH_REINDEX_TASK: {"queue": SEARCH_QUEUE}})
logger = logging.getLogger(__name__)


@celery_app.task(name=SEARCH_REINDEX_TASK, ignore_result=False)
def rebuild_index() -> dict[str, object]:
    return asyncio.run(_rebuild_index())


async def _rebuild_index() -> dict[str, object]:
    async with SessionLocal() as session:
        summary = await rebuild_public_video_index(session)
    payload = {"document_count": summary.document_count, "task_uid": summary.task_uid}
    logger.info("sector=G stage=search_reindex_complete %s", payload)
    return payload
