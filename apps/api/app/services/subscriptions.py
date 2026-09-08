from uuid import UUID

from fastapi import HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Channel, ChannelSubscription, User, Video, WatchHistory
from app.domain.visibility import discoverable_video, owner_or_direct_link_readable_video


async def subscribe(session: AsyncSession, user: User, channel_id: UUID, response: Response) -> None:
    channel = await session.get(Channel, channel_id)
    if channel is None:
        raise HTTPException(status_code=404, detail={"error": "NotFound", "message": "Channel not found"})
    existing = await session.scalar(select(ChannelSubscription).where(ChannelSubscription.user_id == user.id, ChannelSubscription.channel_id == channel_id))
    if existing is None:
        session.add(ChannelSubscription(user_id=user.id, channel_id=channel_id))
        await session.commit(); response.status_code = status.HTTP_201_CREATED
    else:
        response.status_code = status.HTTP_200_OK


async def unsubscribe(session: AsyncSession, user: User, channel_id: UUID) -> None:
    existing = await session.scalar(select(ChannelSubscription).where(ChannelSubscription.user_id == user.id, ChannelSubscription.channel_id == channel_id))
    if existing is not None:
        await session.delete(existing); await session.commit()


async def subscription_feed(session: AsyncSession, user: User) -> list[Video]:
    subscribed = select(ChannelSubscription.channel_id).where(ChannelSubscription.user_id == user.id)
    visible = Video.channel_id.in_(subscribed) & discoverable_video()
    result = await session.execute(select(Video).options(selectinload(Video.channel)).where(visible).order_by(Video.created_at.desc()))
    return list(result.scalars())


async def record_history(session: AsyncSession, user: User | None, video: Video, position_seconds: object) -> None:
    if user is None:
        return
    item = await session.scalar(select(WatchHistory).where(WatchHistory.user_id == user.id, WatchHistory.video_id == video.id))
    if item is None:
        session.add(WatchHistory(user_id=user.id, video_id=video.id, position_seconds=position_seconds))
    else:
        item.position_seconds = position_seconds
        item.watched_at = func.now()


async def history(session: AsyncSession, user: User) -> list[WatchHistory]:
    result = await session.execute(
        select(WatchHistory)
        .join(Video, Video.id == WatchHistory.video_id)
        .options(selectinload(WatchHistory.video).selectinload(Video.channel))
        .where(WatchHistory.user_id == user.id, owner_or_direct_link_readable_video(user.id))
        .order_by(WatchHistory.watched_at.desc())
    )
    return list(result.scalars())
