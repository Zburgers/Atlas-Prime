from __future__ import annotations

import logging
import time
from datetime import timedelta
from typing import Annotated
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, Path, Query, Request, Response, UploadFile, status
from fastapi.responses import RedirectResponse

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
from app.schemas.feed import FeedItemResponse, FeedResponse
from app.schemas.videos import (
    PlaybackEventCreate,
    PlaybackEventResponse,
    PlaybackResponse,
    ProcessingJobResponse,
    ProcessingStatusResponse,
    UserResponse,
    VideoCreate,
    VideoEngagementResponse,
    VideoImpressionCreate,
    VideoImpressionResponse,
    VideoListItemResponse,
    VideoListResponse,
    VideoResponse,
    VideoUploadResponse,
    VideoViewCreate,
    VideoViewResponse,
    VideoUpdate,
)
from app.services import analytics as analytics_service
from app.services import playback_delivery
from app.services import feed as feed_service
from app.services import reactions as reactions_service
from app.services import uploads as upload_service
from app.services import videos as video_service
from app.services import subscriptions as subscription_service
from app.services.storage import HlsObjectNotFoundError
from app.core import config

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


def _thumbnail_url_for(video: object) -> str | None:
    if getattr(video, "status", None) != VideoStatus.READY.value:
        return None
    if not getattr(video, "thumbnail_storage_key", None):
        return None
    return f"/videos/{video.id}/thumbnail"


def video_list_item(video: object) -> VideoListItemResponse:
    channel = getattr(video, "channel", None)
    return VideoListItemResponse.model_validate(video).model_copy(
        update={
            "thumbnail_url": _thumbnail_url_for(video),
            "channel_handle": getattr(channel, "handle", None),
            "channel_display_name": getattr(channel, "display_name", None),
        }
    )


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
    return VideoListResponse(items=[video_list_item(video) for video in items], total=total, page=page, page_size=page_size)


@router.get("/videos/{video_id}", response_model=VideoResponse)
async def get_video(video_id: UUID, session: SessionDep, user: OptionalCurrentUserDep) -> object:
    return await video_service.get_video_for_read(session, user, video_id)


@router.get("/videos/{video_id}/related", response_model=FeedResponse)
async def related_videos(
    video_id: UUID,
    session: SessionDep,
    user: OptionalCurrentUserDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 10,
    request_id: Annotated[str | None, Query(max_length=120)] = None,
) -> FeedResponse:
    resolved_request_id, ranked_videos, total = await feed_service.related_videos(
        session, user=user, video_id=video_id, page=page, page_size=page_size, request_id=request_id
    )
    return FeedResponse(
        request_id=resolved_request_id,
        surface=feed_service.RELATED_SURFACE,
        algorithm_version=feed_service.RELATED_ALGORITHM_VERSION,
        items=[FeedItemResponse(request_id=resolved_request_id, surface=feed_service.RELATED_SURFACE, rank=item.rank, score=item.score, reason=item.reason, video=video_list_item(item.video)) for item in ranked_videos],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.patch("/videos/{video_id}", response_model=VideoResponse)
async def update_video(video_id: UUID, payload: VideoUpdate, session: SessionDep, user: CurrentUserDep) -> object:
    return await video_service.update_video(session, user, video_id, payload)


@router.delete("/videos/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_video(
    video_id: UUID,
    session: SessionDep,
    user: CurrentUserDep,
    original_storage: OriginalStorageDep,
    processed_storage: ProcessedHlsStorageDep,
) -> Response:
    await video_service.delete_video(session, user, video_id, original_storage, processed_storage)
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
        size_bytes=result.size_bytes,
        content_type=result.content_type,
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
    master_playlist_url = f"/videos/{video.id}/hls/master.m3u8" if video.hls_master_storage_key else None
    if master_playlist_url and config.playback_delivery_mode() == "signed-redirect":
        if not config.minio_public_endpoint():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"error": "ServiceUnavailable", "message": "Signed playback delivery is not configured"},
            )
        try:
            token = playback_delivery.issue_token(
                video_id=str(video.id),
                token_version=video.playback_token_version,
                viewer_id=str(user.id) if user else None,
                ttl=timedelta(seconds=config.playback_token_ttl_seconds()),
            )
        except playback_delivery.PlaybackTokenError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"error": "ServiceUnavailable", "message": "Signed playback delivery is not configured"},
            ) from None
        master_playlist_url = f"/videos/{video.id}/delivery/master.m3u8?token={quote(token, safe='')}"
    return PlaybackResponse(
        video_id=video.id,
        status=VideoStatus(video.status),
        master_playlist_url=master_playlist_url,
        thumbnail_url=f"/videos/{video.id}/thumbnail" if video.thumbnail_storage_key else None,
        renditions=list(video.renditions),
        text_tracks=[
            {"id": track.id, "language": track.language, "label": track.label, "kind": track.kind, "default": track.is_default, "url": f"/videos/{video.id}/captions/{track.id}", "created_at": track.created_at}
            for track in sorted(video.text_tracks, key=lambda item: (not item.is_default, item.language))
        ],
        chapters=[{"title": chapter.title, "start_seconds": chapter.start_seconds} for chapter in sorted(video.chapters, key=lambda item: item.position)],
    )


@router.get("/videos/{video_id}/hls/{asset_path:path}")
async def hls_asset(
    video_id: UUID,
    asset_path: Annotated[str, Path(min_length=1)],
    request: Request,
    session: SessionDep,
    user: OptionalCurrentUserDep,
    storage: ProcessedHlsStorageDep,
) -> Response:
    request_id = request.state.request_id
    try:
        video = await video_service.video_with_renditions_for_playback(session, user, video_id)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_403_FORBIDDEN:
            logger.warning(
                "sector=G stage=hls_asset_denied request_id=%s video_id=%s user_id=%s asset_path=%s",
                request_id,
                video_id,
                getattr(user, "id", None),
                asset_path,
            )
        raise
    storage_key, media_type, cache_control = _resolve_hls_asset(video, asset_path)
    try:
        hls_object = storage.get_hls_object(key=storage_key)
    except HlsObjectNotFoundError:
        logger.warning(
            "sector=G stage=hls_asset_missing request_id=%s video_id=%s storage_key=%s asset_path=%s",
            request_id,
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


@router.get("/videos/{video_id}/delivery/{asset_path:path}")
async def signed_delivery_asset(
    video_id: UUID,
    asset_path: Annotated[str, Path(min_length=1)],
    token: Annotated[str, Query(min_length=1)],
    session: SessionDep,
    user: OptionalCurrentUserDep,
    storage: ProcessedHlsStorageDep,
) -> Response:
    if not config.minio_public_endpoint():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "ServiceUnavailable", "message": "Signed playback delivery is not configured"},
        )
    video = await video_service.video_with_renditions_for_signed_delivery(session, video_id)
    try:
        claims = playback_delivery.verify_token(token, video_id=str(video.id), token_version=video.playback_token_version)
    except playback_delivery.PlaybackTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Unauthorized", "message": "Invalid playback token"},
        ) from None
    if claims.viewer_id is not None and (user is None or str(user.id) != claims.viewer_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "Forbidden", "message": "Playback token is not valid for this viewer"},
        )

    storage_key, media_type, cache_control = _resolve_hls_asset(video, asset_path)
    if media_type == PLAYLIST_MEDIA_TYPE:
        try:
            hls_object = storage.get_hls_object(key=storage_key)
        except HlsObjectNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "NotFound", "message": "HLS asset not found"},
            ) from None
        headers = {"Cache-Control": cache_control}
        if hls_object.etag:
            headers["ETag"] = hls_object.etag
        return Response(
            content=_rewrite_delivery_playlist(hls_object.body, token),
            media_type=PLAYLIST_MEDIA_TYPE,
            headers=headers,
        )

    expires_in = max(1, claims.expires_at - int(time.time()))
    return RedirectResponse(
        url=storage.presign_hls_object(key=storage_key, expires_in=expires_in),
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        headers={"Cache-Control": cache_control},
    )


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
        request_id=payload.request_id,
    )
    session.add(event)
    if payload.event_type == "play":
        await subscription_service.record_history(session, user, video, payload.position_seconds)
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


@router.post("/videos/{video_id}/impressions", response_model=VideoImpressionResponse, status_code=status.HTTP_201_CREATED)
async def record_video_impression(
    video_id: UUID,
    payload: VideoImpressionCreate,
    session: SessionDep,
    user: OptionalCurrentUserDep,
) -> object:
    return await analytics_service.record_impression(session, user, video_id, payload)


@router.post("/videos/{video_id}/views", response_model=VideoViewResponse)
async def record_video_view(
    video_id: UUID,
    payload: VideoViewCreate,
    response: Response,
    session: SessionDep,
    user: OptionalCurrentUserDep,
) -> VideoViewResponse:
    return await analytics_service.record_view(session, user, video_id, payload, response)


@router.get("/videos/{video_id}/engagement", response_model=VideoEngagementResponse)
async def get_video_engagement(
    video_id: UUID,
    session: SessionDep,
    user: CurrentUserDep,
) -> VideoEngagementResponse:
    return await reactions_service.get_engagement(session, user, video_id)


@router.post("/videos/{video_id}/like", response_model=VideoEngagementResponse)
async def like_video(
    video_id: UUID,
    response: Response,
    session: SessionDep,
    user: CurrentUserDep,
) -> VideoEngagementResponse:
    return await reactions_service.like_video(session, user, video_id, response)


@router.delete("/videos/{video_id}/like", response_model=VideoEngagementResponse)
async def unlike_video(
    video_id: UUID,
    session: SessionDep,
    user: CurrentUserDep,
) -> VideoEngagementResponse:
    return await reactions_service.unlike_video(session, user, video_id)


@router.post("/videos/{video_id}/watch-later", response_model=VideoEngagementResponse)
async def save_video_for_later(
    video_id: UUID,
    response: Response,
    session: SessionDep,
    user: CurrentUserDep,
) -> VideoEngagementResponse:
    return await reactions_service.save_video(session, user, video_id, response)


@router.delete("/videos/{video_id}/watch-later", response_model=VideoEngagementResponse)
async def remove_video_from_watch_later(
    video_id: UUID,
    session: SessionDep,
    user: CurrentUserDep,
) -> VideoEngagementResponse:
    return await reactions_service.remove_saved_video(session, user, video_id)


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


def _rewrite_delivery_playlist(body: bytes, token: str) -> bytes:
    encoded_token = quote(token, safe="")
    rewritten: list[str] = []
    for line in body.decode("utf-8").splitlines(keepends=True):
        uri = line.rstrip("\r\n")
        line_ending = line[len(uri) :]
        if uri and not uri.startswith("#"):
            rewritten.append(f"{uri}?token={encoded_token}{line_ending}")
        else:
            rewritten.append(line)
    return "".join(rewritten).encode()


def _invalid_hls_path() -> HTTPException:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={"error": "BadRequest", "message": "Invalid HLS asset path"},
    )
