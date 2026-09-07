from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import User, Video, VideoProcessingJob
from app.db.session import SessionLocal
from app.domain.status import DeletionStatus, JobStatus, ModerationStatus, ProcessingStage, VideoStatus, validate_video_transition
from app.schemas.videos import ProcessingStatusJobResponse, ProcessingStatusResponse, VideoCreate, VideoUpdate
from app.services.channels import ensure_default_channel
from app.services.processing_dispatch import queue_processing_job
from app.services.processing_queue import ProcessingQueue
from app.services.storage import OriginalStorage, ProcessedHlsStorage
from app.domain.visibility import discoverable_video, is_direct_link_readable_video

logger = logging.getLogger(__name__)


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
    channel = await ensure_default_channel(session, owner)
    video = Video(owner_id=owner.id, channel_id=channel.id, title=payload.title, description=payload.description)
    session.add(video)
    await session.commit()
    await session.refresh(video)
    return video


async def list_visible_videos(session: AsyncSession, user: User | None, page: int, page_size: int) -> tuple[list[Video], int]:
    public_ready = discoverable_video()
    visible = public_ready if user is None else or_(Video.owner_id == user.id, public_ready)
    visible = visible & Video.deleted_at.is_(None)
    total = await session.scalar(select(func.count()).select_from(Video).where(visible))
    result = await session.execute(
        select(Video)
        .options(selectinload(Video.channel))
        .where(visible)
        .order_by(Video.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result.scalars()), int(total or 0)


async def get_video_for_read(session: AsyncSession, user: User | None, video_id: UUID) -> Video:
    video = await session.get(Video, video_id)
    if video is None:
        raise _not_found()
    if video.deleted_at is not None:
        raise _not_found()
    if video.moderation_status == ModerationStatus.REMOVED.value:
        raise _not_found()
    if user is not None and video.owner_id == user.id:
        return video
    if is_direct_link_readable_video(video):
        return video
    raise _forbidden()


async def get_video_for_owner(session: AsyncSession, user: User, video_id: UUID) -> Video:
    video = await session.get(Video, video_id)
    if video is None:
        raise _not_found()
    if video.deleted_at is not None:
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


async def delete_video(
    session: AsyncSession,
    user: User,
    video_id: UUID,
) -> "DeletionResult":
    result = await session.execute(select(Video).where(Video.id == video_id).with_for_update())
    video = result.scalar_one_or_none()
    if video is None:
        raise _not_found()
    if video.owner_id != user.id:
        raise _forbidden()

    now = datetime.now(timezone.utc)
    if video.deleted_at is None:
        video.deleted_at = now
        video.deletion_status = DeletionStatus.PENDING.value
        video.deletion_error = None
        video.active_processing_generation = None

    await session.execute(
        update(VideoProcessingJob)
        .where(
            VideoProcessingJob.video_id == video.id,
            VideoProcessingJob.status.in_((JobStatus.QUEUED.value, JobStatus.RUNNING.value)),
        )
        .values(
            status=JobStatus.CANCELED.value,
            stage=ProcessingStage.FAILED.value,
            finished_at=now,
            error_code="VIDEO_DELETED",
            error_message="Video was deleted before processing completed",
        )
    )
    await session.commit()
    logger.info(
        "sector=B/C/D/G stage=video_tombstoned video_id=%s owner_id=%s deletion_status=%s",
        video.id,
        user.id,
        video.deletion_status,
    )
    return DeletionResult(
        video_id=video.id,
        deletion_status=video.deletion_status,
        should_schedule=video.deletion_status != DeletionStatus.COMPLETE.value,
    )


@dataclass(frozen=True)
class DeletionResult:
    video_id: UUID
    deletion_status: str
    should_schedule: bool


@dataclass(frozen=True)
class DeletionStorageKeys:
    original_storage_key: str | None


async def cleanup_deleted_video(
    video_id: UUID,
    original_storage: OriginalStorage,
    processed_storage: ProcessedHlsStorage,
    *,
    session_factory=None,
) -> str | None:
    """Claim a tombstone, clean storage outside the DB transaction, and finalize it."""
    factory = session_factory or SessionLocal
    try:
        keys = await _claim_deletion_cleanup(video_id, session_factory=factory)
    except Exception:
        logger.exception("sector=C/G stage=video_delete_claim_failed video_id=%s", video_id)
        return None
    if keys is None:
        return None

    errors: list[str] = []
    if keys.original_storage_key:
        try:
            await asyncio.to_thread(original_storage.delete_original, key=keys.original_storage_key)
        except Exception:
            logger.exception("sector=C/G stage=video_delete_original_failed video_id=%s", video_id)
            errors.append("original")

    try:
        deleted_processed = await asyncio.to_thread(processed_storage.delete_video_tree, video_id=video_id)
    except Exception:
        logger.exception("sector=C/G stage=video_delete_processed_failed video_id=%s", video_id)
        errors.append("processed")
        deleted_processed = 0

    if errors:
        await _mark_deletion_failed(video_id, session_factory=factory)
        return DeletionStatus.FAILED.value

    finalized = await _mark_deletion_complete(video_id, session_factory=factory)
    if finalized:
        logger.info(
            "sector=C/G stage=video_deleted video_id=%s processed_objects_deleted=%s",
            video_id,
            deleted_processed,
        )
        return DeletionStatus.COMPLETE.value
    return None


async def _claim_deletion_cleanup(video_id: UUID, *, session_factory) -> DeletionStorageKeys | None:
    async with session_factory() as session:
        result = await session.execute(
            select(Video)
            .where(
                Video.id == video_id,
                Video.deleted_at.is_not(None),
                Video.active_processing_generation.is_(None),
                Video.deletion_status.in_(
                    (
                        DeletionStatus.PENDING.value,
                        DeletionStatus.RUNNING.value,
                        DeletionStatus.FAILED.value,
                    )
                ),
            )
            .with_for_update()
        )
        video = result.scalar_one_or_none()
        if video is None:
            await session.rollback()
            return None
        keys = DeletionStorageKeys(original_storage_key=video.original_storage_key)
        video.deletion_status = DeletionStatus.RUNNING.value
        video.deletion_error = None
        await session.commit()
        logger.info("sector=C/G stage=video_delete_claimed video_id=%s deletion_status=running", video_id)
        return keys


async def _mark_deletion_failed(video_id: UUID, *, session_factory) -> None:
    try:
        async with session_factory() as session:
            result = await session.execute(
                update(Video)
                .where(
                    Video.id == video_id,
                    Video.deleted_at.is_not(None),
                    Video.active_processing_generation.is_(None),
                    Video.deletion_status == DeletionStatus.RUNNING.value,
                )
                .values(
                    deletion_status=DeletionStatus.FAILED.value,
                    deletion_error="Storage cleanup failed; retry reconciliation",
                )
                .returning(Video.id)
            )
            marked = result.scalar_one_or_none() is not None
            await session.commit()
            if marked:
                logger.error("sector=C/G stage=video_delete_failed video_id=%s", video_id)
    except Exception:
        logger.exception("sector=C/G stage=video_delete_failure_record_failed video_id=%s", video_id)


async def _mark_deletion_complete(video_id: UUID, *, session_factory) -> bool:
    try:
        async with session_factory() as session:
            result = await session.execute(
                update(Video)
                .where(
                    Video.id == video_id,
                    Video.deleted_at.is_not(None),
                    Video.active_processing_generation.is_(None),
                    Video.deletion_status == DeletionStatus.RUNNING.value,
                )
                .values(
                    deletion_status=DeletionStatus.COMPLETE.value,
                    deletion_error=None,
                    original_storage_key=None,
                    hls_master_storage_key=None,
                    thumbnail_storage_key=None,
                )
                .returning(Video.id)
            )
            committed = result.scalar_one_or_none() is not None
            await session.commit()
            return committed
    except Exception:
        logger.exception("sector=C/G stage=video_delete_complete_update_failed video_id=%s", video_id)
        return False


async def transition_video_status(session: AsyncSession, video: Video, target: VideoStatus) -> Video:
    validate_video_transition(VideoStatus(video.status), target)
    video.status = target.value
    if target != VideoStatus.FAILED:
        video.failure_code = None
        video.failure_message = None
    await session.commit()
    await session.refresh(video)
    return video


async def queue_processing_job_for_owner(
    session: AsyncSession,
    user: User,
    video_id: UUID,
    processing_queue: ProcessingQueue,
) -> VideoProcessingJob:
    video = await get_video_for_owner(session, user, video_id)
    if VideoStatus(video.status) != VideoStatus.UPLOADED:
        raise _conflict(
            "Video must be uploaded before processing can be queued",
            {"current_status": video.status, "required_status": VideoStatus.UPLOADED.value},
        )
    return (
        await queue_processing_job(session, video, processing_queue, generation=uuid4())
    ).job


async def processing_status(session: AsyncSession, user: User | None, video_id: UUID) -> ProcessingStatusResponse:
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
        latest_job=(
            ProcessingStatusJobResponse(
                id=job.id,
                video_id=job.video_id,
                status=JobStatus(job.status),
                stage=ProcessingStage(job.stage),
            )
            if (job := result.scalar_one_or_none()) is not None
            else None
        ),
        failure_code=video.failure_code,
        failure_message=video.failure_message,
    )


async def video_with_renditions_for_playback(session: AsyncSession, user: User | None, video_id: UUID) -> Video:
    result = await session.execute(
        select(Video)
        .options(
            selectinload(Video.renditions),
            selectinload(Video.asset_inventory),
            selectinload(Video.text_tracks),
            selectinload(Video.chapters),
        )
        .where(Video.id == video_id)
    )
    video = result.scalar_one_or_none()
    if video is None:
        raise _not_found()
    if video.deleted_at is not None or video.moderation_status == ModerationStatus.REMOVED.value:
        raise _not_found()
    if video.status != VideoStatus.READY.value:
        raise _conflict("Video is not ready for playback", {"current_status": video.status})
    if (user is None or video.owner_id != user.id) and not is_direct_link_readable_video(video):
        raise _forbidden()
    return video


async def video_with_renditions_for_signed_delivery(session: AsyncSession, video_id: UUID) -> Video:
    result = await session.execute(
        select(Video)
        .options(selectinload(Video.renditions), selectinload(Video.asset_inventory))
        .where(Video.id == video_id)
    )
    video = result.scalar_one_or_none()
    if video is None or video.deleted_at is not None or video.moderation_status == ModerationStatus.REMOVED.value:
        raise _not_found()
    if video.status != VideoStatus.READY.value:
        raise _conflict("Video is not ready for playback", {"current_status": video.status})
    return video
