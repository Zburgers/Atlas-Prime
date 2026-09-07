from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Playlist, PlaylistItem, User, Video
from app.domain.visibility import is_discoverable_video
from app.schemas.playlists import PlaylistCreate
from app.services import videos as video_service


def _not_found() -> HTTPException:
    return HTTPException(status_code=404, detail={"error": "NotFound", "message": "Playlist not found"})


def _forbidden() -> HTTPException:
    return HTTPException(status_code=403, detail={"error": "Forbidden", "message": "You do not have access to this playlist"})


async def create(session: AsyncSession, user: User, payload: PlaylistCreate) -> Playlist:
    playlist = Playlist(owner_id=user.id, title=payload.title, description=payload.description, privacy=payload.privacy)
    session.add(playlist); await session.commit()
    return await _with_items(session, playlist.id)


async def _with_items(session: AsyncSession, playlist_id: UUID) -> Playlist:
    result = await session.execute(
        select(Playlist)
        .options(selectinload(Playlist.items).selectinload(PlaylistItem.video).selectinload(Video.channel))
        .where(Playlist.id == playlist_id)
    )
    playlist = result.scalar_one_or_none()
    if playlist is None:
        raise _not_found()
    return playlist


async def for_owner(session: AsyncSession, user: User, playlist_id: UUID) -> Playlist:
    playlist = await session.get(Playlist, playlist_id)
    if playlist is None:
        raise _not_found()
    if playlist.owner_id != user.id:
        raise _forbidden()
    return playlist


async def for_read(session: AsyncSession, user: User | None, playlist_id: UUID) -> Playlist:
    playlist = await _with_items(session, playlist_id)
    if playlist is None or (playlist.privacy != "public" and (user is None or playlist.owner_id != user.id)):
        raise _not_found()
    return playlist


async def add_item(session: AsyncSession, user: User, playlist_id: UUID, video_id: UUID) -> PlaylistItem:
    playlist = await for_owner(session, user, playlist_id)
    playlist = await session.scalar(select(Playlist).where(Playlist.id == playlist.id).with_for_update())
    if playlist is None:
        raise _not_found()
    video = await video_service.get_video_for_read(session, user, video_id)
    if not is_discoverable_video(video):
        raise HTTPException(status_code=409, detail={"error": "Conflict", "message": "Only public ready videos can be added to playlists"})
    if await session.scalar(select(PlaylistItem).where(PlaylistItem.playlist_id == playlist.id, PlaylistItem.video_id == video.id)):
        raise HTTPException(status_code=409, detail={"error": "Conflict", "message": "Video is already in this playlist"})
    max_position = await session.scalar(select(func.max(PlaylistItem.position)).where(PlaylistItem.playlist_id == playlist.id))
    position = int(max_position if max_position is not None else -1) + 1
    item = PlaylistItem(playlist_id=playlist.id, video_id=video.id, position=position)
    item.video = video
    session.add(item); await session.commit()
    result = await session.execute(select(PlaylistItem).options(selectinload(PlaylistItem.video).selectinload(Video.channel)).where(PlaylistItem.id == item.id))
    return result.scalar_one()


async def remove_item(session: AsyncSession, user: User, playlist_id: UUID, item_id: UUID) -> None:
    playlist = await for_owner(session, user, playlist_id)
    item = await session.scalar(select(PlaylistItem).where(PlaylistItem.id == item_id, PlaylistItem.playlist_id == playlist.id))
    if item is None:
        raise _not_found()
    await session.delete(item); await session.commit()
