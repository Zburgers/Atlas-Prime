from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, Response, UploadFile, status

from app.api.deps import CurrentUserDep, OptionalCurrentUserDep, ProcessedHlsStorageDep, SessionDep
from app.schemas.thumbnails import ThumbnailListResponse, ThumbnailResponse
from app.services import thumbnails as thumbnail_service
from app.services import videos as video_service
from app.services.storage import HlsObjectNotFoundError

router = APIRouter(tags=["thumbnails"])


def _response(thumbnail: object, video_id: UUID) -> ThumbnailResponse:
    return ThumbnailResponse(
        id=thumbnail.id, source=thumbnail.source, content_type=thumbnail.content_type,
        width=thumbnail.width, height=thumbnail.height, selected=thumbnail.selected,
        url=f"/videos/{video_id}/thumbnail", created_at=thumbnail.created_at,
    )


@router.get("/studio/videos/{video_id}/thumbnails", response_model=ThumbnailListResponse)
async def list_video_thumbnails(video_id: UUID, session: SessionDep, user: CurrentUserDep) -> ThumbnailListResponse:
    items = await thumbnail_service.list_thumbnails(session, user, video_id)
    return ThumbnailListResponse(items=[_response(item, video_id) for item in items])


@router.post("/studio/videos/{video_id}/thumbnails", response_model=ThumbnailResponse, status_code=status.HTTP_201_CREATED)
async def upload_video_thumbnail(
    video_id: UUID, session: SessionDep, user: CurrentUserDep, storage: ProcessedHlsStorageDep,
    file: Annotated[UploadFile, File(description="JPEG or PNG thumbnail")],
) -> ThumbnailResponse:
    thumbnail = await thumbnail_service.upload_custom_thumbnail(session, user, video_id, file, storage)
    return _response(thumbnail, video_id)


@router.post("/studio/videos/{video_id}/thumbnails/{thumbnail_id}/select", response_model=ThumbnailResponse)
async def select_video_thumbnail(video_id: UUID, thumbnail_id: UUID, session: SessionDep, user: CurrentUserDep) -> ThumbnailResponse:
    return _response(await thumbnail_service.select_thumbnail(session, user, video_id, thumbnail_id), video_id)


@router.get("/videos/{video_id}/thumbnail")
async def selected_thumbnail(video_id: UUID, session: SessionDep, user: OptionalCurrentUserDep, storage: ProcessedHlsStorageDep) -> Response:
    video = await video_service.get_video_for_read(session, user, video_id)
    if not video.thumbnail_storage_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "NotFound", "message": "Thumbnail not found"})
    try:
        thumbnail = storage.get_hls_object(key=video.thumbnail_storage_key)
    except HlsObjectNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "NotFound", "message": "Thumbnail not found"}) from None
    headers = {"Cache-Control": "private, max-age=300"}
    if thumbnail.etag:
        headers["ETag"] = thumbnail.etag
    if thumbnail.content_length is not None:
        headers["Content-Length"] = str(thumbnail.content_length)
    return Response(content=thumbnail.body, media_type=thumbnail.content_type or "image/jpeg", headers=headers)
