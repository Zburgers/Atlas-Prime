from __future__ import annotations

import logging
import tempfile
from dataclasses import dataclass
from pathlib import PurePath
from typing import BinaryIO

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import upload_max_bytes
from app.db.models import User, Video, VideoProcessingJob
from app.domain.status import JobStatus, VideoStatus, validate_video_transition
from app.services import videos as video_service
from app.services.processing_queue import ProcessingQueue
from app.services.storage import OriginalStorage

logger = logging.getLogger(__name__)

CHUNK_SIZE = 1024 * 1024
SPOOL_MAX_SIZE = 8 * 1024 * 1024

ALLOWED_UPLOADS = {
    "mp4": {"video/mp4", "application/mp4"},
    "m4v": {"video/x-m4v", "video/mp4"},
    "mov": {"video/quicktime"},
    "webm": {"video/webm"},
}


@dataclass(frozen=True)
class UploadedVideoResult:
    video: Video
    processing_job: VideoProcessingJob
    storage_key: str
    size_bytes: int
    content_type: str
    celery_task_id: str


async def upload_original_and_queue_processing(
    session: AsyncSession,
    *,
    user: User,
    video_id,
    file: UploadFile,
    storage: OriginalStorage,
    processing_queue: ProcessingQueue,
) -> UploadedVideoResult:
    video = await video_service.get_video_for_owner(session, user, video_id)
    _ensure_upload_allowed(video)

    validate_video_transition(VideoStatus(video.status), VideoStatus.UPLOADING)
    video.status = VideoStatus.UPLOADING.value
    video.failure_code = None
    video.failure_message = None
    await session.commit()
    await session.refresh(video)

    try:
        buffered, size_bytes, header, extension, content_type = await _buffer_and_validate_upload(file)
        stored = storage.put_original(
            video_id=video.id,
            extension=extension,
            body=buffered,
            size_bytes=size_bytes,
            content_type=content_type,
        )
        validate_video_transition(VideoStatus(video.status), VideoStatus.UPLOADED)
        video.original_storage_key = stored.key
        video.status = VideoStatus.UPLOADED.value
        await session.commit()
        await session.refresh(video)

        result = await _queue_uploaded_video(session, video, processing_queue)
        logger.info(
            "sector=C stage=upload_queued video_id=%s job_id=%s bytes=%s key=%s",
            video.id,
            result.processing_job.id,
            size_bytes,
            stored.key,
        )
        return UploadedVideoResult(
            video=result.video,
            processing_job=result.processing_job,
            storage_key=stored.key,
            size_bytes=size_bytes,
            content_type=content_type,
            celery_task_id=result.celery_task_id,
        )
    except HTTPException as exc:
        await _mark_video_failed(session, video, "UPLOAD_VALIDATION_FAILED", _public_error_message(exc))
        raise
    except Exception:
        logger.exception("sector=C stage=upload_failed video_id=%s", video.id)
        await _mark_video_failed(session, video, "UPLOAD_FAILED", "Upload failed before processing could be queued")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": "UploadFailed", "message": "Upload failed before processing could be queued"},
        ) from None
    finally:
        await file.close()


@dataclass(frozen=True)
class QueuedVideoResult:
    video: Video
    processing_job: VideoProcessingJob
    celery_task_id: str


async def _queue_uploaded_video(
    session: AsyncSession,
    video: Video,
    processing_queue: ProcessingQueue,
) -> QueuedVideoResult:
    if not video.original_storage_key:
        raise RuntimeError("uploaded video is missing original storage key")
    validate_video_transition(VideoStatus(video.status), VideoStatus.QUEUED)
    job = VideoProcessingJob(video_id=video.id, status=JobStatus.QUEUED.value)
    video.status = VideoStatus.QUEUED.value
    session.add(job)
    await session.flush()
    try:
        celery_task_id = processing_queue.enqueue_video_processing(
            video_id=video.id,
            job_id=job.id,
            original_storage_key=video.original_storage_key,
        )
    except Exception:
        await session.rollback()
        await session.refresh(video)
        await _mark_video_failed(session, video, "UPLOAD_ENQUEUE_FAILED", "Upload stored but processing could not be queued")
        raise
    await session.commit()
    await session.refresh(video)
    await session.refresh(job)
    return QueuedVideoResult(video=video, processing_job=job, celery_task_id=celery_task_id)


def _ensure_upload_allowed(video: Video) -> None:
    status_value = VideoStatus(video.status)
    if status_value not in {VideoStatus.DRAFT, VideoStatus.UPLOADING, VideoStatus.FAILED}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "Conflict",
                "message": "Video cannot accept an original upload in its current state",
                "details": {"current_status": video.status},
            },
        )


async def _buffer_and_validate_upload(file: UploadFile) -> tuple[BinaryIO, int, bytes, str, str]:
    extension = _extension_from_filename(file.filename)
    content_type = (file.content_type or "").lower()
    if extension not in ALLOWED_UPLOADS or content_type not in ALLOWED_UPLOADS[extension]:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail={"error": "UnsupportedMediaType", "message": "Upload must be an MP4, M4V, MOV, or WebM video"},
        )

    max_bytes = upload_max_bytes()
    size_bytes = 0
    header = b""
    buffered = tempfile.SpooledTemporaryFile(max_size=SPOOL_MAX_SIZE, mode="w+b")
    while True:
        chunk = await file.read(CHUNK_SIZE)
        if not chunk:
            break
        if not header:
            header = chunk[:64]
        size_bytes += len(chunk)
        if size_bytes > max_bytes:
            buffered.close()
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail={
                    "error": "UploadTooLarge",
                    "message": "Upload exceeds the configured file size limit",
                    "details": {"max_bytes": max_bytes},
                },
            )
        buffered.write(chunk)

    if size_bytes == 0:
        buffered.close()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "BadRequest", "message": "Upload file is empty"},
        )

    if not _header_matches_video_container(extension, header):
        buffered.close()
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail={"error": "UnsupportedMediaType", "message": "Upload content does not match the declared video container"},
        )

    buffered.seek(0)
    return buffered, size_bytes, header, extension, content_type


def _extension_from_filename(filename: str | None) -> str:
    suffix = PurePath(filename or "").suffix.lower().lstrip(".")
    if not suffix:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail={"error": "UnsupportedMediaType", "message": "Upload filename must include a supported extension"},
        )
    return suffix


def _header_matches_video_container(extension: str, header: bytes) -> bool:
    if extension in {"mp4", "m4v", "mov"}:
        return len(header) >= 12 and header[4:8] == b"ftyp"
    if extension == "webm":
        return header.startswith(b"\x1a\x45\xdf\xa3")
    return False


async def _mark_video_failed(session: AsyncSession, video: Video, code: str, message: str) -> None:
    try:
        validate_video_transition(VideoStatus(video.status), VideoStatus.FAILED)
    except Exception:
        pass
    video.status = VideoStatus.FAILED.value
    video.failure_code = code
    video.failure_message = message
    await session.commit()


def _public_error_message(exc: HTTPException) -> str:
    detail = exc.detail
    if isinstance(detail, dict) and isinstance(detail.get("message"), str):
        return detail["message"]
    return "Upload validation failed"
