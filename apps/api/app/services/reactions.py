from __future__ import annotations

from uuid import UUID

from fastapi import Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, VideoReaction, VideoSave
from app.schemas.videos import VideoEngagementResponse
from app.services import videos as video_service

LIKE_REACTION = "like"


async def get_engagement(session: AsyncSession, user: User, video_id: UUID) -> VideoEngagementResponse:
    video = await video_service.get_video_for_read(session, user, video_id)
    liked = await _liked(session, user, video.id)
    saved = await _saved(session, user, video.id)
    return VideoEngagementResponse(
        video_id=video.id,
        liked=liked,
        like_count=video.like_count,
        saved_to_watch_later=saved,
    )


async def like_video(session: AsyncSession, user: User, video_id: UUID, response: Response) -> VideoEngagementResponse:
    video = await video_service.get_video_for_read(session, user, video_id)
    existing = await _reaction(session, user, video.id)
    if existing is None:
        session.add(VideoReaction(user_id=user.id, video_id=video.id, reaction_type=LIKE_REACTION))
        video.like_count += 1
        await session.commit()
        response.status_code = status.HTTP_201_CREATED
    else:
        response.status_code = status.HTTP_200_OK
    return await get_engagement(session, user, video.id)


async def unlike_video(session: AsyncSession, user: User, video_id: UUID) -> VideoEngagementResponse:
    video = await video_service.get_video_for_read(session, user, video_id)
    existing = await _reaction(session, user, video.id)
    if existing is not None:
        await session.delete(existing)
        video.like_count = max(0, video.like_count - 1)
        await session.commit()
    return await get_engagement(session, user, video.id)


async def save_video(session: AsyncSession, user: User, video_id: UUID, response: Response) -> VideoEngagementResponse:
    video = await video_service.get_video_for_read(session, user, video_id)
    existing = await _save(session, user, video.id)
    if existing is None:
        session.add(VideoSave(user_id=user.id, video_id=video.id))
        await session.commit()
        response.status_code = status.HTTP_201_CREATED
    else:
        response.status_code = status.HTTP_200_OK
    return await get_engagement(session, user, video.id)


async def remove_saved_video(session: AsyncSession, user: User, video_id: UUID) -> VideoEngagementResponse:
    video = await video_service.get_video_for_read(session, user, video_id)
    existing = await _save(session, user, video.id)
    if existing is not None:
        await session.delete(existing)
        await session.commit()
    return await get_engagement(session, user, video.id)


async def _reaction(session: AsyncSession, user: User, video_id: UUID) -> VideoReaction | None:
    return await session.scalar(
        select(VideoReaction)
        .where(
            VideoReaction.user_id == user.id,
            VideoReaction.video_id == video_id,
            VideoReaction.reaction_type == LIKE_REACTION,
        )
        .limit(1)
    )


async def _save(session: AsyncSession, user: User, video_id: UUID) -> VideoSave | None:
    return await session.scalar(
        select(VideoSave)
        .where(
            VideoSave.user_id == user.id,
            VideoSave.video_id == video_id,
        )
        .limit(1)
    )


async def _liked(session: AsyncSession, user: User, video_id: UUID) -> bool:
    reaction = await _reaction(session, user, video_id)
    return reaction is not None


async def _saved(session: AsyncSession, user: User, video_id: UUID) -> bool:
    save = await _save(session, user, video_id)
    return save is not None
