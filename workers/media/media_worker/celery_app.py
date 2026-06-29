import os

from celery import Celery


celery_app = Celery(
    "atlas_media_worker",
    broker=os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/1"),
)
celery_app.conf.task_default_queue = "media"
celery_app.conf.worker_prefetch_multiplier = 1
celery_app.conf.task_acks_late = True


@celery_app.task(name="media_worker.health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "media-worker"}


@celery_app.task(name="media_worker.process_video")
def process_video(video_id: str, job_id: str, original_storage_key: str) -> dict[str, str]:
    return {
        "status": "pending-sector-d",
        "video_id": video_id,
        "job_id": job_id,
        "original_storage_key": original_storage_key,
    }
