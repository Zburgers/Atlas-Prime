from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import SessionDep
from app.domain.status import VideoStatus
from app.schemas.search import SearchResponse
from app.schemas.videos import VideoListItemResponse
from app.services import search as search_service

router = APIRouter()


def _thumbnail_url_for(video: object) -> str | None:
    if getattr(video, "status", None) != VideoStatus.READY.value:
        return None
    if not getattr(video, "thumbnail_storage_key", None):
        return None
    return f"/videos/{video.id}/thumbnail"


def _video_list_item(video: object, caption_snippet: str | None = None) -> VideoListItemResponse:
    channel = getattr(video, "channel", None)
    return VideoListItemResponse.model_validate(video).model_copy(
        update={
            "thumbnail_url": _thumbnail_url_for(video),
            "channel_handle": getattr(channel, "handle", None),
            "channel_display_name": getattr(channel, "display_name", None),
            "caption_snippet": caption_snippet,
        }
    )


@router.get("/search", response_model=SearchResponse)
async def search_videos(
    session: SessionDep,
    q: Annotated[str, Query(max_length=120)] = "",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> SearchResponse:
    normalized_query = search_service.normalize_search_query(q)
    items, total = await search_service.search_public_videos(session, normalized_query, page, page_size)
    return SearchResponse(
        query=normalized_query,
        items=[_video_list_item(item.video, item.caption_snippet) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )
