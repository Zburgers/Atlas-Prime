import logging
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
logger = logging.getLogger(__name__)


@celery_app.task(name="media_worker.health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "media-worker"}


@celery_app.task(name="media_worker.process_video")
def process_video(video_id: str, job_id: str, generation: str, original_storage_key: str) -> dict[str, str]:
    repository = MediaRepository()
    storage = ObjectStorage()
    source_suffix = Path(original_storage_key).suffix or ".media"
    try:
        logger.info("sector=D stage=processing_started video_id=%s job_id=%s key=%s", video_id, job_id, original_storage_key)
        if not repository.mark_started(video_id=video_id, job_id=job_id, generation=generation, worker_id=config.worker_id()):
            logger.info("sector=D stage=processing_skipped video_id=%s job_id=%s reason=not_queued", video_id, job_id)
            return {"status": "skipped", "video_id": video_id, "job_id": job_id}
        with tempfile.TemporaryDirectory(prefix=f"atlas-{video_id}-") as temp_dir:
            work_dir = Path(temp_dir)
            source_path = work_dir / f"source{source_suffix}"
            logger.info("sector=D stage=original_download video_id=%s job_id=%s", video_id, job_id)
            storage.download_original(original_storage_key, source_path)

            if not repository.mark_stage(video_id=video_id, job_id=job_id, generation=generation, stage="probing"):
                logger.info("sector=D stage=processing_skipped video_id=%s job_id=%s reason=stale_generation", video_id, job_id)
                return {"status": "skipped", "video_id": video_id, "job_id": job_id}
            probe = probe_media(source_path)
            logger.info(
                "sector=D stage=probe_complete video_id=%s job_id=%s duration=%s width=%s height=%s video_codec=%s audio_codec=%s",
                video_id,
                job_id,
                probe.duration_seconds,
                probe.width,
                probe.height,
                probe.video_codec,
                probe.audio_codec,
            )
            if not repository.mark_processing(video_id=video_id, job_id=job_id, generation=generation, probe=probe):
                logger.info("sector=D stage=processing_skipped video_id=%s job_id=%s reason=stale_generation", video_id, job_id)
                return {"status": "skipped", "video_id": video_id, "job_id": job_id}

            package_result = package_to_hls(
                video_id=video_id,
                generation=generation,
                source=source_path,
                output_root=work_dir / "processed",
                probe=probe,
            )
            if not repository.mark_stage(video_id=video_id, job_id=job_id, generation=generation, stage="uploading"):
                logger.info("sector=D stage=processing_skipped video_id=%s job_id=%s reason=stale_generation", video_id, job_id)
                return {"status": "skipped", "video_id": video_id, "job_id": job_id}
            uploaded_assets = storage.upload_hls_tree(
                video_id=video_id,
                generation=generation,
                hls_root=package_result.hls_root,
            )
            logger.info(
                "sector=D stage=hls_upload_complete video_id=%s job_id=%s renditions=%s uploaded_objects=%s",
                video_id,
                job_id,
                ",".join(rendition.label for rendition in package_result.renditions),
                len(uploaded_assets),
            )
            publication = repository.mark_succeeded(
                video_id=video_id,
                job_id=job_id,
                generation=generation,
                master_key=package_result.master_storage_key,
                thumbnail_key=package_result.thumbnail_storage_key,
                generated_thumbnail_keys=package_result.generated_thumbnail_storage_keys,
                renditions=package_result.renditions,
                uploaded_assets=uploaded_assets,
            )
            if not publication.applied:
                logger.info(
                    "sector=D stage=processing_skipped video_id=%s job_id=%s generation=%s reason=%s",
                    video_id,
                    job_id,
                    generation,
                    publication.reason or "stale_terminal",
                )
                _cleanup_hls_tree(
                    storage,
                    video_id=video_id,
                    job_id=job_id,
                    generation=generation,
                    stage="stale_attempt_cleanup",
                )
                return {"status": "skipped", "video_id": video_id, "job_id": job_id}
            if publication.old_generation and publication.old_generation != generation:
                _cleanup_hls_tree(
                    storage,
                    video_id=video_id,
                    job_id=job_id,
                    generation=publication.old_generation,
                    stage="prior_attempt_cleanup",
                )
            return {
                "status": "ready",
                "video_id": video_id,
                "job_id": job_id,
                "uploaded_objects": str(len(uploaded_assets)),
            }
    except ProcessingError as exc:
        logger.warning(
            "sector=D stage=processing_failed video_id=%s job_id=%s failure_code=%s",
            video_id,
            job_id,
            exc.code,
        )
        _cleanup_hls_tree(storage, video_id=video_id, job_id=job_id, generation=generation)
        applied = repository.mark_failed(
            video_id=video_id,
            job_id=job_id,
            generation=generation,
            failure=ProcessingFailure(code=exc.code, message=exc.safe_message),
        )
        if not applied:
            logger.info("sector=D stage=processing_skipped video_id=%s job_id=%s reason=stale_terminal", video_id, job_id)
            return {"status": "skipped", "video_id": video_id, "job_id": job_id}
        return {"status": "failed", "video_id": video_id, "job_id": job_id, "failure_code": exc.code}
    except Exception as exc:
        logger.exception("sector=D stage=processing_exception video_id=%s job_id=%s", video_id, job_id)
        _cleanup_hls_tree(storage, video_id=video_id, job_id=job_id, generation=generation)
        applied = repository.mark_failed(
            video_id=video_id,
            job_id=job_id,
            generation=generation,
            failure=ProcessingFailure(code="PROCESSING_FAILED", message="Media processing failed"),
        )
        if not applied:
            logger.info("sector=D stage=processing_skipped video_id=%s job_id=%s reason=stale_terminal", video_id, job_id)
            return {"status": "skipped", "video_id": video_id, "job_id": job_id}
        return {
            "status": "failed",
            "video_id": video_id,
            "job_id": job_id,
            "failure_code": "PROCESSING_FAILED",
            "detail": exc.__class__.__name__,
        }


def _cleanup_hls_tree(
    storage: ObjectStorage,
    *,
    video_id: str,
    job_id: str,
    generation: str,
    stage: str = "partial_hls_cleanup",
) -> None:
    try:
        deleted = storage.delete_hls_tree(video_id=video_id, generation=generation)
        logger.info(
            "sector=D stage=%s video_id=%s job_id=%s generation=%s deleted_objects=%s",
            stage,
            video_id,
            job_id,
            generation,
            deleted,
        )
    except Exception:
        logger.exception(
            "sector=D stage=%s_failed video_id=%s job_id=%s generation=%s",
            stage,
            video_id,
            job_id,
            generation,
        )
