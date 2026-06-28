from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import User, Video, VideoProcessingJob
from app.domain.status import JobStatus, VideoPrivacy, VideoStatus, validate_video_transition
from app.schemas.videos import ProcessingStatusResponse, VideoCreate, VideoUpdate


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"error": "NotFound", "message": "Video not found"},
    )


def _forbidden() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={"error": "Forbidden", "message": "You do not have access to this video"},
    )


def _conflict(message: str, details: dict[str, object] | None = None) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={"error": "Conflict", "message": message, "details": details},
    )


async def create_video(session: AsyncSession, owner: User, payload: VideoCreate) -> Video:
    video = Video(owner_id=owner.id, title=payload.title, description=payload.description)
    session.add(video)
    await session.commit()
    await session.refresh(video)
    return video


async def list_visible_videos(session: AsyncSession, user: User, page: int, page_size: int) -> tuple[list[Video], int]:
    visible = or_(
        Video.owner_id == user.id,
        (Video.status == VideoStatus.READY.value) & (Video.privacy.in_([VideoPrivacy.PUBLIC.value, VideoPrivacy.UNLISTED.value])),
    )
    total = await session.scalar(select(func.count()).select_from(Video).where(visible))
    result = await session.execute(
        select(Video)
        .where(visible)
        .order_by(Video.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result.scalars()), int(total or 0)


async def get_video_for_read(session: AsyncSession, user: User, video_id: UUID) -> Video:
    video = await session.get(Video, video_id)
    if video is None:
        raise _not_found()
    if video.owner_id == user.id:
        return video
    if video.status == VideoStatus.READY.value and video.privacy in {VideoPrivacy.PUBLIC.value, VideoPrivacy.UNLISTED.value}:
        return video
    raise _forbidden()


async def get_video_for_owner(session: AsyncSession, user: User, video_id: UUID) -> Video:
    video = await session.get(Video, video_id)
    if video is None:
        raise _not_found()
    if video.owner_id != user.id:
        raise _forbidden()
    return video


async def update_video(session: AsyncSession, user: User, video_id: UUID, payload: VideoUpdate) -> Video:
    video = await get_video_for_owner(session, user, video_id)
    if payload.title is not None:
        video.title = payload.title
    if payload.description is not None:
        video.description = payload.description
    if payload.privacy is not None:
        video.privacy = payload.privacy.value
    await session.commit()
    await session.refresh(video)
    return video


async def delete_video(session: AsyncSession, user: User, video_id: UUID) -> None:
    video = await get_video_for_owner(session, user, video_id)
    await session.delete(video)
    await session.commit()


async def transition_video_status(session: AsyncSession, video: Video, target: VideoStatus) -> Video:
    validate_video_transition(VideoStatus(video.status), target)
    video.status = target.value
    if target != VideoStatus.FAILED:
        video.failure_code = None
        video.failure_message = None
    await session.commit()
    await session.refresh(video)
    return video


async def queue_processing_job(session: AsyncSession, user: User, video_id: UUID) -> VideoProcessingJob:
    video = await get_video_for_owner(session, user, video_id)
    if VideoStatus(video.status) != VideoStatus.UPLOADED:
        raise _conflict(
            "Video must be uploaded before processing can be queued",
            {"current_status": video.status, "required_status": VideoStatus.UPLOADED.value},
        )
    validate_video_transition(VideoStatus(video.status), VideoStatus.QUEUED)
    job = VideoProcessingJob(video_id=video.id, status=JobStatus.QUEUED.value)
    video.status = VideoStatus.QUEUED.value
    session.add(job)
    await session.commit()
    await session.refresh(job)
    return job


async def processing_status(session: AsyncSession, user: User, video_id: UUID) -> ProcessingStatusResponse:
    video = await get_video_for_read(session, user, video_id)
    result = await session.execute(
        select(VideoProcessingJob)
        .where(VideoProcessingJob.video_id == video.id)
        .order_by(VideoProcessingJob.created_at.desc())
        .limit(1)
    )
    return ProcessingStatusResponse(
        video_id=video.id,
        video_status=VideoStatus(video.status),
        latest_job=result.scalar_one_or_none(),
        failure_code=video.failure_code,
        failure_message=video.failure_message,
    )


async def video_with_renditions_for_playback(session: AsyncSession, user: User, video_id: UUID) -> Video:
    result = await session.execute(
        select(Video).options(selectinload(Video.renditions)).where(Video.id == video_id)
    )
    video = result.scalar_one_or_none()
    if video is None:
        raise _not_found()
    if video.status != VideoStatus.READY.value:
        raise _conflict("Video is not ready for playback", {"current_status": video.status})
    if video.owner_id != user.id and video.privacy not in {VideoPrivacy.PUBLIC.value, VideoPrivacy.UNLISTED.value}:
        raise _forbidden()
    return video
