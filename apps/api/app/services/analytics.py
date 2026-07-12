from __future__ import annotations

from uuid import UUID

from fastapi import Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, VideoImpression, VideoView
from app.domain.events import VIEW_COUNT_THRESHOLD_SECONDS
from app.schemas.videos import VideoImpressionCreate, VideoViewCreate, VideoViewResponse
from app.services import videos as video_service


async def record_impression(
    session: AsyncSession,
    user: User | None,
    video_id: UUID,
    payload: VideoImpressionCreate,
) -> VideoImpression:
    video = await video_service.get_video_for_read(session, user, video_id)
    impression = VideoImpression(
        user_id=getattr(user, "id", None),
        video_id=video.id,
        surface=payload.surface,
        position=payload.position,
        request_id=payload.request_id,
    )
    video.impression_count += 1
    session.add(impression)
    await session.commit()
    await session.refresh(impression)
    return impression


async def record_view(
    session: AsyncSession,
    user: User | None,
    video_id: UUID,
    payload: VideoViewCreate,
    response: Response,
) -> VideoViewResponse:
    video = await video_service.get_video_for_read(session, user, video_id)
    if payload.position_seconds < VIEW_COUNT_THRESHOLD_SECONDS:
        response.status_code = status.HTTP_202_ACCEPTED
        return VideoViewResponse(
            video_id=video.id,
            counted=False,
            view_count=video.view_count,
            threshold_seconds=VIEW_COUNT_THRESHOLD_SECONDS,
        )

    existing = await session.scalar(
        select(VideoView)
        .where(VideoView.video_id == video.id, VideoView.session_id == payload.session_id)
        .limit(1)
    )
    if existing is not None:
        response.status_code = status.HTTP_200_OK
        return VideoViewResponse(
            video_id=video.id,
            counted=False,
            view_count=video.view_count,
            threshold_seconds=VIEW_COUNT_THRESHOLD_SECONDS,
        )

    view = VideoView(
        user_id=getattr(user, "id", None),
        video_id=video.id,
        session_id=payload.session_id,
        position_seconds=payload.position_seconds,
        request_id=payload.request_id,
    )
    video.view_count += 1
    session.add(view)
    await session.commit()
    response.status_code = status.HTTP_201_CREATED
    return VideoViewResponse(
        video_id=video.id,
        counted=True,
        view_count=video.view_count,
        threshold_seconds=VIEW_COUNT_THRESHOLD_SECONDS,
    )
