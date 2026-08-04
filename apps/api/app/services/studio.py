from __future__ import annotations

import logging
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import User, Video, VideoProcessingJob
from app.domain.status import JobStatus, VideoPrivacy, VideoStatus, validate_video_transition
from app.schemas.studio import StudioVideoUpdate
from app.services import videos as video_service
from app.services.processing_queue import ProcessingQueue

logger = logging.getLogger(__name__)


def _conflict(message: str, details: dict[str, object] | None = None) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={"error": "Conflict", "message": message, "details": details},
    )


async def list_creator_videos(
    session: AsyncSession,
    user: User,
    *,
    page: int,
    page_size: int,
    status_filter: VideoStatus | None = None,
    privacy_filter: VideoPrivacy | None = None,
) -> tuple[list[Video], int]:
    filters = [Video.owner_id == user.id]
    if status_filter is not None:
        filters.append(Video.status == status_filter.value)
    if privacy_filter is not None:
        filters.append(Video.privacy == privacy_filter.value)

    total = await session.scalar(select(func.count()).select_from(Video).where(*filters))
    result = await session.execute(
        select(Video)
        .options(selectinload(Video.channel))
        .where(*filters)
        .order_by(Video.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result.scalars()), int(total or 0)


async def update_creator_video(session: AsyncSession, user: User, video_id: UUID, payload: StudioVideoUpdate) -> Video:
    video = await video_service.get_video_for_owner(session, user, video_id)
    if payload.title is not None:
        video.title = payload.title
    if payload.description is not None:
        video.description = payload.description
    if payload.privacy is not None:
        video.privacy = payload.privacy.value
    await session.commit()
    await session.refresh(video)
    return video


async def processing_timeline(session: AsyncSession, user: User, video_id: UUID) -> list[VideoProcessingJob]:
    video = await video_service.get_video_for_owner(session, user, video_id)
    result = await session.execute(
        select(VideoProcessingJob)
        .where(VideoProcessingJob.video_id == video.id)
        .order_by(VideoProcessingJob.created_at, VideoProcessingJob.id)
    )
    return list(result.scalars())


async def rotate_playback_token(session: AsyncSession, user: User, video_id: UUID) -> int:
    video = await video_service.get_video_for_owner(session, user, video_id)
    video.playback_token_version += 1
    await session.commit()
    return video.playback_token_version


async def retry_failed_video(
    session: AsyncSession,
    user: User,
    video_id: UUID,
    processing_queue: ProcessingQueue,
) -> VideoProcessingJob:
    video = await video_service.get_video_for_owner(session, user, video_id)
    if VideoStatus(video.status) != VideoStatus.FAILED:
        raise _conflict("Only failed videos can be retried", {"current_status": video.status})
    if not video.original_storage_key:
        raise _conflict("Video cannot be retried without an uploaded original", {"current_status": video.status})

    validate_video_transition(VideoStatus(video.status), VideoStatus.QUEUED)
    generation = uuid4()
    job = VideoProcessingJob(video_id=video.id, generation=generation, status=JobStatus.QUEUED.value)
    video.active_processing_generation = generation
    video.status = VideoStatus.QUEUED.value
    video.failure_code = None
    video.failure_message = None
    session.add(job)
    await session.flush()
    try:
        processing_queue.enqueue_video_processing(
            video_id=video.id,
            job_id=job.id,
            generation=job.generation,
            original_storage_key=video.original_storage_key,
        )
    except Exception as exc:
        await session.rollback()
        logger.exception("sector=A/B stage=studio_retry_enqueue_failed video_id=%s", video.id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": "RetryFailed", "message": "Processing retry could not be queued"},
        ) from exc

    await session.commit()
    await session.refresh(job)
    return job
