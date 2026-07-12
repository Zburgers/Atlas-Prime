from __future__ import annotations

import io
import re
import uuid
from dataclasses import dataclass
from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, VideoTextTrack
from app.domain.status import VideoStatus
from app.services import videos as video_service
from app.services.storage import ProcessedHlsStorage

MAX_CAPTION_BYTES = 2 * 1024 * 1024
LANGUAGE_PATTERN = re.compile(r"^[a-z]{2,3}(?:-[A-Z]{2})?$")


@dataclass(frozen=True)
class ValidatedCaption:
    data: bytes
    language: str
    label: str


async def list_captions(session: AsyncSession, user: User, video_id: UUID) -> list[VideoTextTrack]:
    await video_service.get_video_for_owner(session, user, video_id)
    result = await session.execute(
        select(VideoTextTrack)
        .where(VideoTextTrack.video_id == video_id)
        .order_by(VideoTextTrack.is_default.desc(), VideoTextTrack.language)
    )
    return list(result.scalars())


async def upload_caption(
    session: AsyncSession,
    user: User,
    video_id: UUID,
    file: UploadFile,
    storage: ProcessedHlsStorage,
    *,
    language: str,
    label: str,
    is_default: bool,
) -> VideoTextTrack:
    video = await video_service.get_video_for_owner(session, user, video_id)
    if video.status != VideoStatus.READY.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"error": "Conflict", "message": "Video must be ready before uploading captions"})
    try:
        payload = await _validate_caption(file, language=language, label=label)
        track = await session.scalar(
            select(VideoTextTrack).where(
                VideoTextTrack.video_id == video.id,
                VideoTextTrack.language == payload.language,
                VideoTextTrack.kind == "captions",
            )
        )
        has_track = track is not None
        if track is None:
            track = VideoTextTrack(
                video_id=video.id,
                language=payload.language,
                label=payload.label,
                storage_key=f"processed/{video.id}/captions/{payload.language}/{uuid.uuid4()}.vtt",
                is_default=is_default,
            )
        else:
            track.label = payload.label
            track.storage_key = f"processed/{video.id}/captions/{payload.language}/{uuid.uuid4()}.vtt"
            track.is_default = is_default or track.is_default
        if is_default or not has_track:
            existing_default = await session.scalar(
                select(VideoTextTrack.id)
                .where(VideoTextTrack.video_id == video.id, VideoTextTrack.is_default.is_(True), VideoTextTrack.id != track.id)
                .limit(1)
            )
            if existing_default is None:
                track.is_default = True
        if track.is_default:
            await session.execute(
                update(VideoTextTrack)
                .where(VideoTextTrack.video_id == video.id, VideoTextTrack.id != track.id, VideoTextTrack.is_default.is_(True))
                .values(is_default=False)
            )
        storage.put_caption(key=track.storage_key, body=io.BytesIO(payload.data), content_type="text/vtt")
        session.add(track)
        await session.commit()
        await session.refresh(track)
        return track
    finally:
        await file.close()


async def caption_for_read(session: AsyncSession, user: User | None, video_id: UUID, track_id: UUID) -> VideoTextTrack:
    await video_service.get_video_for_read(session, user, video_id)
    track = await session.scalar(select(VideoTextTrack).where(VideoTextTrack.id == track_id, VideoTextTrack.video_id == video_id))
    if track is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "NotFound", "message": "Caption track not found"})
    return track


async def _validate_caption(file: UploadFile, *, language: str, label: str) -> ValidatedCaption:
    normalized_language = language.strip()
    if not LANGUAGE_PATTERN.fullmatch(normalized_language):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"error": "InvalidCaption", "message": "Language must be a BCP 47 language tag such as en or en-US"})
    normalized_label = label.strip()
    if not normalized_label or len(normalized_label) > 80:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"error": "InvalidCaption", "message": "Caption label must be between 1 and 80 characters"})
    filename = (file.filename or "").lower()
    content_type = (file.content_type or "").lower()
    data = await file.read(MAX_CAPTION_BYTES + 1)
    if len(data) > MAX_CAPTION_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail={"error": "UploadTooLarge", "message": "Caption file exceeds the 2 MiB limit"})
    if content_type not in {"text/vtt", "application/octet-stream"} or not filename.endswith(".vtt") or not data.lstrip(b"\xef\xbb\xbf").startswith(b"WEBVTT"):
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail={"error": "UnsupportedMediaType", "message": "Caption file must be a WebVTT (.vtt) file"})
    return ValidatedCaption(data=data, language=normalized_language, label=normalized_label)
