from __future__ import annotations

import io
import uuid
from dataclasses import dataclass
from typing import BinaryIO
from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, VideoThumbnail
from app.domain.status import VideoStatus
from app.services import videos as video_service
from app.services.storage import ProcessedHlsStorage

MAX_THUMBNAIL_BYTES = 5 * 1024 * 1024
MIN_DIMENSION = 64
MAX_DIMENSION = 8192


@dataclass(frozen=True)
class ValidatedThumbnail:
    data: bytes
    extension: str
    content_type: str
    width: int
    height: int


async def list_thumbnails(session: AsyncSession, user: User, video_id: UUID) -> list[VideoThumbnail]:
    await video_service.get_video_for_owner(session, user, video_id)
    result = await session.execute(
        select(VideoThumbnail).where(VideoThumbnail.video_id == video_id).order_by(VideoThumbnail.selected.desc(), VideoThumbnail.created_at)
    )
    return list(result.scalars())


async def upload_custom_thumbnail(
    session: AsyncSession,
    user: User,
    video_id: UUID,
    file: UploadFile,
    storage: ProcessedHlsStorage,
) -> VideoThumbnail:
    video = await video_service.get_video_for_owner(session, user, video_id)
    if video.status != VideoStatus.READY.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"error": "Conflict", "message": "Video must be ready before changing its thumbnail"})
    try:
        payload = await _validate_thumbnail(file)
        key = f"processed/{video.id}/thumbnails/custom/{uuid.uuid4()}.{payload.extension}"
        storage.put_thumbnail(key=key, body=io.BytesIO(payload.data), content_type=payload.content_type)
        await session.execute(update(VideoThumbnail).where(VideoThumbnail.video_id == video.id, VideoThumbnail.selected.is_(True)).values(selected=False))
        thumbnail = VideoThumbnail(
            video_id=video.id,
            storage_key=key,
            source="custom",
            content_type=payload.content_type,
            width=payload.width,
            height=payload.height,
            selected=True,
        )
        video.thumbnail_storage_key = key
        session.add(thumbnail)
        await session.commit()
        await session.refresh(thumbnail)
        return thumbnail
    finally:
        await file.close()


async def select_thumbnail(session: AsyncSession, user: User, video_id: UUID, thumbnail_id: UUID) -> VideoThumbnail:
    video = await video_service.get_video_for_owner(session, user, video_id)
    thumbnail = await session.scalar(
        select(VideoThumbnail).where(VideoThumbnail.id == thumbnail_id, VideoThumbnail.video_id == video.id)
    )
    if thumbnail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "NotFound", "message": "Thumbnail not found"})
    await session.execute(update(VideoThumbnail).where(VideoThumbnail.video_id == video.id, VideoThumbnail.selected.is_(True)).values(selected=False))
    thumbnail.selected = True
    video.thumbnail_storage_key = thumbnail.storage_key
    await session.commit()
    await session.refresh(thumbnail)
    return thumbnail


async def _validate_thumbnail(file: UploadFile) -> ValidatedThumbnail:
    content_type = (file.content_type or "").lower()
    data = await file.read(MAX_THUMBNAIL_BYTES + 1)
    if len(data) > MAX_THUMBNAIL_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail={"error": "UploadTooLarge", "message": "Thumbnail exceeds the 5 MiB limit"})
    if content_type == "image/png" and data.startswith(b"\x89PNG\r\n\x1a\n") and data[12:16] == b"IHDR":
        width, height = int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")
        extension = "png"
    elif content_type == "image/jpeg" and data.startswith(b"\xff\xd8"):
        width, height = _jpeg_dimensions(data)
        extension = "jpg"
    else:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail={"error": "UnsupportedMediaType", "message": "Thumbnail must be a PNG or JPEG image"})
    if not (MIN_DIMENSION <= width <= MAX_DIMENSION and MIN_DIMENSION <= height <= MAX_DIMENSION):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"error": "InvalidThumbnail", "message": "Thumbnail dimensions must be between 64 and 8192 pixels"})
    return ValidatedThumbnail(data=data, extension=extension, content_type=content_type, width=width, height=height)


def _jpeg_dimensions(data: bytes) -> tuple[int, int]:
    offset = 2
    while offset + 9 < len(data):
        if data[offset] != 0xFF:
            break
        marker = data[offset + 1]
        offset += 2
        if marker in {0xD8, 0xD9}:
            continue
        length = int.from_bytes(data[offset:offset + 2], "big")
        if marker in {0xC0, 0xC1, 0xC2} and length >= 7:
            return int.from_bytes(data[offset + 5:offset + 7], "big"), int.from_bytes(data[offset + 3:offset + 5], "big")
        offset += length
    raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail={"error": "UnsupportedMediaType", "message": "Thumbnail content does not match a JPEG image"})
