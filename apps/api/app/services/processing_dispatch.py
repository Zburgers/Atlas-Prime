from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import ProcessingDispatch, Video, VideoProcessingJob
from app.domain.status import JobStatus, VideoStatus, validate_video_transition
from app.services.processing_queue import ProcessingQueue

logger = logging.getLogger(__name__)


class ProcessingPublicationError(RuntimeError):
    """The durable queue intent exists, but broker publication needs reconciliation."""


@dataclass(frozen=True)
class QueuedProcessing:
    job: VideoProcessingJob
    task_id: str


async def queue_processing_job(
    session: AsyncSession,
    video: Video,
    processing_queue: ProcessingQueue,
    *,
    generation: UUID,
) -> QueuedProcessing:
    if not video.original_storage_key:
        raise RuntimeError("queued video is missing original storage key")
    validate_video_transition(VideoStatus(video.status), VideoStatus.QUEUED)
    video.active_processing_generation = generation
    video.status = VideoStatus.QUEUED.value
    video.failure_code = None
    video.failure_message = None
    job = VideoProcessingJob(video_id=video.id, generation=generation, status=JobStatus.QUEUED.value)
    session.add(job)
    await session.flush()
    session.add(ProcessingDispatch(job_id=job.id))
    await session.commit()
    return QueuedProcessing(job=job, task_id=await publish_pending_processing_job(session, job.id, processing_queue))


async def publish_pending_processing_job(
    session: AsyncSession,
    job_id: UUID,
    processing_queue: ProcessingQueue,
) -> str:
    result = await session.execute(
        select(ProcessingDispatch)
        .options(selectinload(ProcessingDispatch.job).selectinload(VideoProcessingJob.video))
        .where(ProcessingDispatch.job_id == job_id, ProcessingDispatch.status == "pending")
        .with_for_update()
    )
    dispatch = result.scalar_one_or_none()
    if dispatch is None:
        existing = await session.scalar(select(ProcessingDispatch).where(ProcessingDispatch.job_id == job_id))
        if existing is not None and existing.status == "published":
            return str(job_id)
        raise ProcessingPublicationError("processing dispatch is not publishable")

    job = dispatch.job
    if job.status != JobStatus.QUEUED.value or job.video.deleted_at is not None:
        dispatch.status = "canceled"
        await session.commit()
        raise ProcessingPublicationError("processing dispatch was canceled")

    dispatch.attempt_count += 1
    try:
        task_id = processing_queue.enqueue_video_processing(
            video_id=job.video_id,
            job_id=job.id,
            generation=job.generation,
            original_storage_key=job.video.original_storage_key or "",
        )
    except Exception as exc:
        dispatch.last_error = "Broker publication failed; retry reconciliation"
        await session.commit()
        logger.exception("sector=B/G stage=processing_publish_failed video_id=%s job_id=%s", job.video_id, job.id)
        raise ProcessingPublicationError from exc

    dispatch.status = "published"
    dispatch.published_at = datetime.now(timezone.utc)
    dispatch.last_error = None
    await session.commit()
    return str(task_id)
