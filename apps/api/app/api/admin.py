from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUserDep, SessionDep
from app.db.models import Video, VideoProcessingJob
from app.schemas.videos import ProcessingJobResponse, VideoResponse

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/jobs", response_model=list[ProcessingJobResponse])
async def list_jobs(
    session: SessionDep,
    _user: CurrentUserDep,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[VideoProcessingJob]:
    result = await session.execute(
        select(VideoProcessingJob).order_by(VideoProcessingJob.created_at.desc()).limit(limit)
    )
    return list(result.scalars())


@router.get("/videos/{video_id}/debug", response_model=VideoResponse)
async def video_debug(video_id: UUID, session: SessionDep, _user: CurrentUserDep) -> Video | None:
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
    return video
