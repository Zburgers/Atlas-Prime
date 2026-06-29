from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUserDep, ProcessingQueueDep, SessionDep
from app.db.models import PlaybackEvent, Video, VideoProcessingJob
from app.domain.status import VideoStatus
from app.schemas.videos import AdminJobResponse, AdminOpsResponse, AdminVideoDebugResponse, VideoResponse

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/ops", response_model=AdminOpsResponse)
async def ops_status(_user: CurrentUserDep, processing_queue: ProcessingQueueDep) -> AdminOpsResponse:
    worker = processing_queue.inspect_workers()
    queue = processing_queue.inspect_queue()
    status_value = "ok" if worker.ok and queue.ok else "degraded"
    return AdminOpsResponse(
        status=status_value,
        api={"ok": True, "service": "api"},
        worker={
            "ok": worker.ok,
            "online_workers": worker.online_workers,
            "active_queues": worker.active_queues,
            "error": worker.error,
        },
        redis={
            "ok": queue.ok,
            "media_queue_depth": queue.media_queue_depth,
            "error": queue.error,
        },
    )


@router.get("/videos", response_model=list[VideoResponse])
async def list_admin_videos(
    session: SessionDep,
    _user: CurrentUserDep,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[Video]:
    result = await session.execute(select(Video).order_by(Video.created_at.desc()).limit(limit))
    return list(result.scalars())


@router.get("/jobs", response_model=list[AdminJobResponse])
async def list_jobs(
    session: SessionDep,
    _user: CurrentUserDep,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[AdminJobResponse]:
    result = await session.execute(
        select(VideoProcessingJob, Video)
        .join(Video, Video.id == VideoProcessingJob.video_id)
        .order_by(VideoProcessingJob.created_at.desc())
        .limit(limit)
    )
    return [
        AdminJobResponse.model_validate(job).model_copy(
            update={
                "video_title": video.title,
                "video_status": VideoStatus(video.status),
                "video_failure_code": video.failure_code,
                "video_failure_message": video.failure_message,
            }
        )
        for job, video in result.all()
    ]


@router.get("/videos/{video_id}/debug", response_model=AdminVideoDebugResponse)
async def video_debug(video_id: UUID, session: SessionDep, _user: CurrentUserDep) -> AdminVideoDebugResponse:
    result = await session.execute(
        select(Video)
        .options(selectinload(Video.renditions), selectinload(Video.processing_jobs))
        .where(Video.id == video_id)
    )
    video = result.scalar_one_or_none()
    if video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NotFound", "message": "Video not found"},
        )
    events_result = await session.execute(
        select(PlaybackEvent)
        .where(PlaybackEvent.video_id == video.id)
        .order_by(PlaybackEvent.created_at.desc())
        .limit(25)
    )
    return AdminVideoDebugResponse(
        video=VideoResponse.model_validate(video),
        renditions=list(video.renditions),
        processing_jobs=sorted(video.processing_jobs, key=lambda job: job.created_at, reverse=True),
        recent_playback_events=list(events_result.scalars()),
    )
