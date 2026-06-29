from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, Path, Query, Response, UploadFile, status

from app.db.models import PlaybackEvent
from app.api.deps import (
    CurrentUserDep,
    OptionalCurrentUserDep,
    OriginalStorageDep,
    ProcessedHlsStorageDep,
    ProcessingQueueDep,
    SessionDep,
)
from app.domain.status import VideoStatus
from app.schemas.videos import (
    PlaybackEventCreate,
    PlaybackEventResponse,
    PlaybackResponse,
    ProcessingJobResponse,
    ProcessingStatusResponse,
    UserResponse,
    VideoCreate,
    VideoListResponse,
    VideoResponse,
    VideoUploadResponse,
    VideoUpdate,
)
from app.services import uploads as upload_service
from app.services import videos as video_service
from app.services.storage import HlsObjectNotFoundError

router = APIRouter()
logger = logging.getLogger(__name__)

PLAYLIST_MEDIA_TYPE = "application/vnd.apple.mpegurl"
SEGMENT_MEDIA_TYPES = {
    ".ts": "video/mp2t",
    ".m4s": "video/iso.segment",
    ".mp4": "video/mp4",
}
THUMBNAIL_MEDIA_TYPE = "image/jpeg"
PLAYLIST_CACHE_CONTROL = "private, no-cache"
THUMBNAIL_CACHE_CONTROL = "private, max-age=300"
SEGMENT_CACHE_CONTROL = "private, max-age=31536000, immutable"


@router.get("/me", response_model=UserResponse)
async def me(user: CurrentUserDep) -> object:
    return user


@router.post("/videos", response_model=VideoResponse, status_code=status.HTTP_201_CREATED)
async def create_video(payload: VideoCreate, session: SessionDep, user: CurrentUserDep) -> object:
    return await video_service.create_video(session, user, payload)


@router.get("/videos", response_model=VideoListResponse)
async def list_videos(
    session: SessionDep,
    user: OptionalCurrentUserDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> VideoListResponse:
    items, total = await video_service.list_visible_videos(session, user, page, page_size)
    return VideoListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/videos/{video_id}", response_model=VideoResponse)
async def get_video(video_id: UUID, session: SessionDep, user: OptionalCurrentUserDep) -> object:
    return await video_service.get_video_for_read(session, user, video_id)


@router.patch("/videos/{video_id}", response_model=VideoResponse)
async def update_video(video_id: UUID, payload: VideoUpdate, session: SessionDep, user: CurrentUserDep) -> object:
    return await video_service.update_video(session, user, video_id, payload)


@router.delete("/videos/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_video(video_id: UUID, session: SessionDep, user: CurrentUserDep) -> Response:
    await video_service.delete_video(session, user, video_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/videos/{video_id}/process", response_model=ProcessingJobResponse, status_code=status.HTTP_201_CREATED)
async def process_video(video_id: UUID, session: SessionDep, user: CurrentUserDep) -> object:
    return await video_service.queue_processing_job(session, user, video_id)


@router.post("/videos/{video_id}/upload", response_model=VideoUploadResponse)
async def upload_video(
    video_id: UUID,
    session: SessionDep,
    user: CurrentUserDep,
    storage: OriginalStorageDep,
    processing_queue: ProcessingQueueDep,
    file: UploadFile = File(...),
) -> VideoUploadResponse:
    result = await upload_service.upload_original_and_queue_processing(
        session,
        user=user,
        video_id=video_id,
        file=file,
        storage=storage,
        processing_queue=processing_queue,
    )
    return VideoUploadResponse(
        video=result.video,
        processing_job=result.processing_job,
        storage_key=result.storage_key,
        size_bytes=result.size_bytes,
        content_type=result.content_type,
        celery_task_id=result.celery_task_id,
    )


@router.get("/videos/{video_id}/processing-status", response_model=ProcessingStatusResponse)
async def get_processing_status(
    video_id: UUID,
    session: SessionDep,
    user: OptionalCurrentUserDep,
) -> ProcessingStatusResponse:
    return await video_service.processing_status(session, user, video_id)


@router.get("/videos/{video_id}/playback", response_model=PlaybackResponse)
async def playback(video_id: UUID, session: SessionDep, user: OptionalCurrentUserDep) -> PlaybackResponse:
    video = await video_service.video_with_renditions_for_playback(session, user, video_id)
    return PlaybackResponse(
        video_id=video.id,
        status=VideoStatus(video.status),
        master_playlist_url=f"/videos/{video.id}/hls/master.m3u8" if video.hls_master_storage_key else None,
        thumbnail_url=f"/videos/{video.id}/hls/thumbnail.jpg" if video.thumbnail_storage_key else None,
        renditions=list(video.renditions),
    )


@router.get("/videos/{video_id}/hls/{asset_path:path}")
async def hls_asset(
    video_id: UUID,
    asset_path: Annotated[str, Path(min_length=1)],
    session: SessionDep,
    user: OptionalCurrentUserDep,
    storage: ProcessedHlsStorageDep,
) -> Response:
    video = await video_service.video_with_renditions_for_playback(session, user, video_id)
    storage_key, media_type, cache_control = _resolve_hls_asset(video, asset_path)
    try:
        hls_object = storage.get_hls_object(key=storage_key)
    except HlsObjectNotFoundError:
        logger.warning(
            "sector=G stage=hls_asset_missing video_id=%s storage_key=%s asset_path=%s",
            video_id,
            storage_key,
            asset_path,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NotFound", "message": "HLS asset not found"},
        ) from None

    headers = {"Cache-Control": cache_control}
    if hls_object.etag:
        headers["ETag"] = hls_object.etag
    if hls_object.content_length is not None:
        headers["Content-Length"] = str(hls_object.content_length)
    return Response(content=hls_object.body, media_type=media_type, headers=headers)


@router.post("/videos/{video_id}/events", response_model=PlaybackEventResponse, status_code=status.HTTP_201_CREATED)
async def record_playback_event(
    video_id: UUID,
    payload: PlaybackEventCreate,
    session: SessionDep,
    user: OptionalCurrentUserDep,
) -> PlaybackEvent:
    video = await video_service.get_video_for_read(session, user, video_id)
    event = PlaybackEvent(
        user_id=getattr(user, "id", None),
        video_id=video.id,
        event_type=payload.event_type,
        position_seconds=payload.position_seconds,
        quality_label=payload.quality_label,
        client_timestamp=payload.client_timestamp,
    )
    session.add(event)
    await session.commit()
    await session.refresh(event)
    if payload.event_type in {"error", "unsupported"}:
        logger.warning(
            "sector=G stage=playback_event video_id=%s user_id=%s event_type=%s position_seconds=%s quality_label=%s",
            video.id,
            getattr(user, "id", None),
            payload.event_type,
            payload.position_seconds,
            payload.quality_label,
        )
    return event


def _resolve_hls_asset(video: object, asset_path: str) -> tuple[str, str, str]:
    if "\\" in asset_path or asset_path.startswith("/") or asset_path.startswith(".") or "//" in asset_path:
        raise _invalid_hls_path()
    parts = asset_path.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise _invalid_hls_path()

    root = f"processed/{video.id}/hls/"
    expected_key = f"{root}{asset_path}"

    if asset_path == "master.m3u8":
        if expected_key != video.hls_master_storage_key:
            raise _invalid_hls_path()
        return expected_key, PLAYLIST_MEDIA_TYPE, PLAYLIST_CACHE_CONTROL

    if asset_path == "thumbnail.jpg":
        if expected_key != video.thumbnail_storage_key:
            raise _invalid_hls_path()
        return expected_key, THUMBNAIL_MEDIA_TYPE, THUMBNAIL_CACHE_CONTROL

    if len(parts) != 2:
        raise _invalid_hls_path()

    rendition_label, filename = parts
    rendition = next((item for item in video.renditions if item.label == rendition_label), None)
    if rendition is None:
        raise _invalid_hls_path()

    if filename == "playlist.m3u8":
        if expected_key != rendition.playlist_storage_key:
            raise _invalid_hls_path()
        return expected_key, PLAYLIST_MEDIA_TYPE, PLAYLIST_CACHE_CONTROL

    suffix = "." + filename.rsplit(".", maxsplit=1)[-1].lower() if "." in filename else ""
    if not filename.startswith("segment_") or suffix not in SEGMENT_MEDIA_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "BadRequest", "message": "Invalid HLS asset path"},
        )
    return expected_key, SEGMENT_MEDIA_TYPES[suffix], SEGMENT_CACHE_CONTROL


def _invalid_hls_path() -> HTTPException:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={"error": "BadRequest", "message": "Invalid HLS asset path"},
    )
