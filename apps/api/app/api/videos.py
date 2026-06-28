from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, Query, Response, status

from app.api.deps import CurrentUserDep, OptionalCurrentUserDep, SessionDep
from app.domain.status import VideoStatus
from app.schemas.videos import (
    PlaybackResponse,
    ProcessingJobResponse,
    ProcessingStatusResponse,
    UserResponse,
    VideoCreate,
    VideoListResponse,
    VideoResponse,
    VideoUpdate,
)
from app.services import videos as video_service

router = APIRouter()


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
) -> None:
    if ".." in asset_path.split("/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "BadRequest", "message": "Invalid HLS asset path"},
        )
    await video_service.video_with_renditions_for_playback(session, user, video_id)
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={"error": "NotImplemented", "message": "HLS proxy is owned by Sector E"},
    )
