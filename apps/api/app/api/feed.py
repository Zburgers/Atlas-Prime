from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import CurrentUserDep, OptionalCurrentUserDep, SessionDep
from app.domain.status import VideoStatus
from app.schemas.feed import FeedItemResponse, FeedResponse, RecommendationDebugResponse
from app.schemas.videos import VideoListItemResponse
from app.services import feed as feed_service
from app.services import recommendation_logging

router = APIRouter(prefix="/feed", tags=["feed"])


def _thumbnail_url_for(video: object) -> str | None:
    if getattr(video, "status", None) != VideoStatus.READY.value:
        return None
    if not getattr(video, "thumbnail_storage_key", None):
        return None
    return f"/videos/{video.id}/thumbnail"


def _video_list_item(video: object) -> VideoListItemResponse:
    channel = getattr(video, "channel", None)
    return VideoListItemResponse.model_validate(video).model_copy(
        update={
            "thumbnail_url": _thumbnail_url_for(video),
            "channel_handle": getattr(channel, "handle", None),
            "channel_display_name": getattr(channel, "display_name", None),
        }
    )


@router.get("/home", response_model=FeedResponse)
async def home_feed(
    session: SessionDep,
    user: OptionalCurrentUserDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    request_id: Annotated[str | None, Query(max_length=120)] = None,
) -> FeedResponse:
    resolved_request_id, ranked_videos, total = await feed_service.home_feed(
        session,
        user=user,
        page=page,
        page_size=page_size,
        request_id=request_id,
    )
    return FeedResponse(
        request_id=resolved_request_id,
        surface=feed_service.HOME_SURFACE,
        algorithm_version=feed_service.home_algorithm_version(),
        items=[
            FeedItemResponse(
                request_id=resolved_request_id,
                surface=feed_service.HOME_SURFACE,
                rank=item.rank,
                score=item.score,
                reason=item.reason,
                video=_video_list_item(item.video),
            )
            for item in ranked_videos
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/requests/{request_id}/debug", response_model=RecommendationDebugResponse)
async def feed_request_debug(
    request_id: str,
    session: SessionDep,
    user: CurrentUserDep,
) -> RecommendationDebugResponse:
    return await recommendation_logging.recommendation_debug(session, request_id=request_id, user=user)
