from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUserDep, ProcessingQueueDep, SessionDep
from app.domain.status import VideoPrivacy, VideoStatus
from app.schemas.studio import StudioVideoListResponse, StudioVideoUpdate
from app.schemas.videos import ProcessingJobResponse, VideoChapterListResponse, VideoChapterReplace, VideoChapterResponse, VideoListItemResponse, VideoResponse
from app.services import chapters as chapters_service
from app.services import studio as studio_service

router = APIRouter(prefix="/studio", tags=["studio"])


def _chapter_list(chapters: list[object]) -> VideoChapterListResponse:
    return VideoChapterListResponse(items=[VideoChapterResponse.model_validate(chapter) for chapter in chapters])


def _thumbnail_url_for(video: object) -> str | None:
    if getattr(video, "status", None) != VideoStatus.READY.value:
        return None
    if not getattr(video, "thumbnail_storage_key", None):
        return None
    return f"/videos/{video.id}/thumbnail"


def _studio_video_item(video: object) -> VideoListItemResponse:
    channel = getattr(video, "channel", None)
    return VideoListItemResponse.model_validate(video).model_copy(
        update={
            "thumbnail_url": _thumbnail_url_for(video),
            "channel_handle": getattr(channel, "handle", None),
            "channel_display_name": getattr(channel, "display_name", None),
        }
    )


@router.get("/videos", response_model=StudioVideoListResponse)
async def list_studio_videos(
    session: SessionDep,
    user: CurrentUserDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    status_filter: Annotated[VideoStatus | None, Query(alias="status")] = None,
    privacy_filter: Annotated[VideoPrivacy | None, Query(alias="privacy")] = None,
) -> StudioVideoListResponse:
    items, total = await studio_service.list_creator_videos(
        session,
        user,
        page=page,
        page_size=page_size,
        status_filter=status_filter,
        privacy_filter=privacy_filter,
    )
    return StudioVideoListResponse(
        items=[_studio_video_item(video) for video in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.patch("/videos/{video_id}", response_model=VideoResponse)
async def update_studio_video(
    video_id: UUID,
    payload: StudioVideoUpdate,
    session: SessionDep,
    user: CurrentUserDep,
) -> object:
    return await studio_service.update_creator_video(session, user, video_id, payload)


@router.post(
    "/videos/{video_id}/retry-processing",
    response_model=ProcessingJobResponse,
    status_code=status.HTTP_201_CREATED,
)
async def retry_studio_video_processing(
    video_id: UUID,
    session: SessionDep,
    user: CurrentUserDep,
    processing_queue: ProcessingQueueDep,
) -> object:
    return await studio_service.retry_failed_video(session, user, video_id, processing_queue)


@router.get("/videos/{video_id}/chapters", response_model=VideoChapterListResponse)
async def list_studio_video_chapters(video_id: UUID, session: SessionDep, user: CurrentUserDep) -> VideoChapterListResponse:
    return _chapter_list(await chapters_service.list_chapters(session, user, video_id))


@router.put("/videos/{video_id}/chapters", response_model=VideoChapterListResponse)
async def replace_studio_video_chapters(
    video_id: UUID,
    payload: VideoChapterReplace,
    session: SessionDep,
    user: CurrentUserDep,
) -> VideoChapterListResponse:
    return _chapter_list(await chapters_service.replace_chapters(session, user, video_id, payload.items))
