from __future__ import annotations

from pydantic import BaseModel

from app.schemas.videos import VideoListItemResponse


class SearchResponse(BaseModel):
    query: str
    items: list[VideoListItemResponse]
    total: int
    page: int
    page_size: int
