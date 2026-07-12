from __future__ import annotations

from pydantic import BaseModel

from app.schemas.videos import VideoListItemResponse


class FeedItemResponse(BaseModel):
    request_id: str
    surface: str
    rank: int
    score: float
    reason: str
    video: VideoListItemResponse


class FeedResponse(BaseModel):
    request_id: str
    surface: str
    algorithm_version: str
    items: list[FeedItemResponse]
    total: int
    page: int
    page_size: int
