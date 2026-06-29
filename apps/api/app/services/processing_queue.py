from __future__ import annotations

from uuid import UUID

from celery import Celery

from app.core import config


class ProcessingQueue:
    task_name = "media_worker.process_video"

    def __init__(self) -> None:
        self._celery = Celery(
            "atlas_api",
            broker=config.celery_broker_url(),
            backend=config.celery_result_backend(),
        )
        self._celery.conf.task_default_queue = "media"

    def enqueue_video_processing(self, *, video_id: UUID, job_id: UUID, original_storage_key: str) -> str:
        result = self._celery.send_task(
            self.task_name,
            kwargs={
                "video_id": str(video_id),
                "job_id": str(job_id),
                "original_storage_key": original_storage_key,
            },
            queue="media",
        )
        return str(result.id)
