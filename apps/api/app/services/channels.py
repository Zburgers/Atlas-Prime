from __future__ import annotations

import re
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Channel, User, Video
from app.domain.visibility import discoverable_video
from app.schemas.channels import ChannelUpdate

RESERVED_HANDLES = {
    "admin",
    "api",
    "channels",
    "me",
    "sign-in",
    "sign-up",
    "upload",
    "videos",
    "watch",
}


def normalize_handle(raw: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", raw.strip().lower()).strip("-")
    normalized = re.sub(r"-+", "-", normalized)
    if len(normalized) > 30:
        normalized = normalized[:30].strip("-")
    if len(normalized) < 3:
        raise _bad_handle()
    if normalized in RESERVED_HANDLES:
        raise _bad_handle("This channel handle is reserved")
    return normalized


def default_display_name(user: User) -> str:
    if user.email and "@" in user.email:
        local_part = user.email.split("@", maxsplit=1)[0].strip()
        if local_part:
            return local_part[:100]
    return user.clerk_user_id[:100]


async def ensure_default_channel(session: AsyncSession, user: User) -> Channel:
    result = await session.execute(select(Channel).where(Channel.owner_user_id == user.id))
    channel = result.scalar_one_or_none()
    if channel is not None:
        await _attach_unassigned_owner_videos(session, user.id, channel.id)
        return channel

    handle = await _unique_handle(session, _default_handle_seed(user), user.id)
    channel = Channel(owner_user_id=user.id, handle=handle, display_name=default_display_name(user))
    session.add(channel)
    await session.flush()
    await _attach_unassigned_owner_videos(session, user.id, channel.id)
    return channel


async def get_my_channel(session: AsyncSession, user: User) -> Channel:
    channel = await ensure_default_channel(session, user)
    await session.commit()
    await session.refresh(channel)
    return channel


async def update_my_channel(session: AsyncSession, user: User, payload: ChannelUpdate) -> Channel:
    channel = await ensure_default_channel(session, user)
    if payload.handle is not None:
        handle = normalize_handle(payload.handle)
        if handle != channel.handle and await _handle_exists(session, handle):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error": "Conflict", "message": "Channel handle is already taken"},
            )
        channel.handle = handle
    if payload.display_name is not None:
        channel.display_name = payload.display_name.strip()
    if payload.description is not None:
        channel.description = payload.description
    await session.commit()
    await session.refresh(channel)
    return channel


async def get_public_channel_with_videos(session: AsyncSession, handle: str) -> tuple[Channel, list[Video]]:
    normalized = normalize_handle(handle)
    result = await session.execute(select(Channel).where(Channel.handle == normalized))
    channel = result.scalar_one_or_none()
    if channel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NotFound", "message": "Channel not found"},
        )
    videos_result = await session.execute(
        select(Video)
        .options(selectinload(Video.channel))
        .where(Video.channel_id == channel.id, discoverable_video())
        .order_by(Video.created_at.desc())
    )
    return channel, list(videos_result.scalars())


async def _attach_unassigned_owner_videos(session: AsyncSession, user_id: UUID, channel_id: UUID) -> None:
    await session.execute(
        update(Video)
        .where(Video.owner_id == user_id, Video.channel_id.is_(None))
        .values(channel_id=channel_id)
    )


async def _unique_handle(session: AsyncSession, seed: str, user_id: UUID) -> str:
    base = normalize_handle(seed)
    if not await _handle_exists(session, base):
        return base
    suffix = str(user_id).split("-", maxsplit=1)[0]
    candidate = f"{base[:21].strip('-')}-{suffix}"
    if not await _handle_exists(session, candidate):
        return candidate
    index = 2
    while True:
        fallback = f"{base[:18].strip('-')}-{suffix[:6]}-{index}"
        if not await _handle_exists(session, fallback):
            return fallback
        index += 1


async def _handle_exists(session: AsyncSession, handle: str) -> bool:
    existing = await session.scalar(select(Channel.id).where(Channel.handle == handle).limit(1))
    return existing is not None


def _default_handle_seed(user: User) -> str:
    if user.email and "@" in user.email:
        return user.email.split("@", maxsplit=1)[0]
    return user.clerk_user_id


def _bad_handle(message: str = "Channel handle must contain at least three letters or numbers") -> HTTPException:
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={"error": "ValidationError", "message": message},
    )
