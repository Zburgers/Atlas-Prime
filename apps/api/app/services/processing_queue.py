from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from celery import Celery
from redis import Redis

from app.core import config


@dataclass(frozen=True)
class WorkerInspection:
    ok: bool
    online_workers: list[str]
    active_queues: dict[str, list[str]]
    error: str | None = None


@dataclass(frozen=True)
class QueueInspection:
    ok: bool
    media_queue_depth: int | None
    error: str | None = None


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

    def inspect_workers(self, *, timeout: float = 1.0) -> WorkerInspection:
        try:
            inspector = self._celery.control.inspect(timeout=timeout)
            pings = inspector.ping() or {}
            active_queues = inspector.active_queues() or {}
        except Exception as exc:
            return WorkerInspection(ok=False, online_workers=[], active_queues={}, error=exc.__class__.__name__)

        workers = sorted(pings.keys())
        queue_map: dict[str, list[str]] = {}
        for worker_name, queues in active_queues.items():
            queue_map[worker_name] = sorted(str(queue.get("name")) for queue in queues if queue.get("name"))
        return WorkerInspection(ok=bool(workers), online_workers=workers, active_queues=queue_map)

    def inspect_queue(self) -> QueueInspection:
        try:
            client = Redis.from_url(config.celery_broker_url())
            try:
                depth = client.llen("media")
            finally:
                client.close()
        except Exception as exc:
            return QueueInspection(ok=False, media_queue_depth=None, error=exc.__class__.__name__)
        return QueueInspection(ok=True, media_queue_depth=int(depth))
