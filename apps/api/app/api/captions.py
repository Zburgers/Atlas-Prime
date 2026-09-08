from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile, status

from app.api.deps import CurrentUserDep, OptionalCurrentUserDep, ProcessedHlsStorageDep, SessionDep
from app.schemas.captions import TextTrackListResponse, TextTrackResponse
from app.services import captions as captions_service
from app.services.storage import HlsObjectNotFoundError

router = APIRouter(tags=["captions"])


def _response(track: object, video_id: UUID) -> TextTrackResponse:
    return TextTrackResponse(
        id=track.id,
        language=track.language,
        label=track.label,
        kind=track.kind,
        default=track.is_default,
        url=f"/videos/{video_id}/captions/{track.id}",
        created_at=track.created_at,
    )


@router.get("/studio/videos/{video_id}/captions", response_model=TextTrackListResponse)
async def list_captions(video_id: UUID, session: SessionDep, user: CurrentUserDep) -> TextTrackListResponse:
    tracks = await captions_service.list_captions(session, user, video_id)
    return TextTrackListResponse(items=[_response(track, video_id) for track in tracks])


@router.post("/studio/videos/{video_id}/captions", response_model=TextTrackResponse, status_code=status.HTTP_201_CREATED)
async def upload_caption(
    video_id: UUID,
    session: SessionDep,
    user: CurrentUserDep,
    storage: ProcessedHlsStorageDep,
    file: Annotated[UploadFile, File(description="WebVTT caption file")],
    language: Annotated[str, Form()],
    label: Annotated[str, Form()],
    is_default: Annotated[bool, Form()] = False,
) -> TextTrackResponse:
    track = await captions_service.upload_caption(
        session,
        user,
        video_id,
        file,
        storage,
        language=language,
        label=label,
        is_default=is_default,
    )
    return _response(track, video_id)


@router.get("/videos/{video_id}/captions/{track_id}")
async def get_caption(
    video_id: UUID,
    track_id: UUID,
    session: SessionDep,
    user: OptionalCurrentUserDep,
    storage: ProcessedHlsStorageDep,
) -> Response:
    track = await captions_service.caption_for_read(session, user, video_id, track_id)
    try:
        caption = storage.get_caption(key=track.storage_key)
    except HlsObjectNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "NotFound", "message": "Caption track not found"}) from None
    headers = {"Cache-Control": "private, max-age=300"}
    if caption.etag:
        headers["ETag"] = caption.etag
    if caption.content_length is not None:
        headers["Content-Length"] = str(caption.content_length)
    return Response(content=caption.body, media_type="text/vtt", headers=headers)
