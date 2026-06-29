import tempfile
from pathlib import Path

from celery import Celery

from media_worker import config
from media_worker.packager import ProcessingError, package_to_hls, probe_media
from media_worker.repository import MediaRepository, ProcessingFailure
from media_worker.storage import ObjectStorage

celery_app = Celery(
    "atlas_media_worker",
    broker=config.celery_broker_url(),
    backend=config.celery_result_backend(),
)
celery_app.conf.task_default_queue = "media"
celery_app.conf.worker_prefetch_multiplier = 1
celery_app.conf.task_acks_late = True


@celery_app.task(name="media_worker.health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "media-worker"}


@celery_app.task(name="media_worker.process_video")
def process_video(video_id: str, job_id: str, original_storage_key: str) -> dict[str, str]:
    repository = MediaRepository()
    storage = ObjectStorage()
    source_suffix = Path(original_storage_key).suffix or ".media"
    try:
        repository.mark_started(video_id=video_id, job_id=job_id, worker_id=config.worker_id())
        with tempfile.TemporaryDirectory(prefix=f"atlas-{video_id}-") as temp_dir:
            work_dir = Path(temp_dir)
            source_path = work_dir / f"source{source_suffix}"
            storage.download_original(original_storage_key, source_path)

            probe = probe_media(source_path)
            repository.mark_processing(video_id=video_id, probe=probe)

            package_result = package_to_hls(
                video_id=video_id,
                source=source_path,
                output_root=work_dir / "processed",
                probe=probe,
            )
            uploaded_keys = storage.upload_hls_tree(video_id=video_id, hls_root=package_result.hls_root)
            repository.mark_succeeded(
                video_id=video_id,
                job_id=job_id,
                master_key=package_result.master_storage_key,
                thumbnail_key=package_result.thumbnail_storage_key,
                renditions=package_result.renditions,
            )
            return {
                "status": "ready",
                "video_id": video_id,
                "job_id": job_id,
                "uploaded_objects": str(len(uploaded_keys)),
            }
    except ProcessingError as exc:
        repository.mark_failed(
            video_id=video_id,
            job_id=job_id,
            failure=ProcessingFailure(code=exc.code, message=exc.safe_message),
        )
        return {"status": "failed", "video_id": video_id, "job_id": job_id, "failure_code": exc.code}
    except Exception as exc:
        repository.mark_failed(
            video_id=video_id,
            job_id=job_id,
            failure=ProcessingFailure(code="PROCESSING_FAILED", message="Media processing failed"),
        )
        return {
            "status": "failed",
            "video_id": video_id,
            "job_id": job_id,
            "failure_code": "PROCESSING_FAILED",
            "detail": exc.__class__.__name__,
        }
