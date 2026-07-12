from __future__ import annotations

from uuid import UUID

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


class RecommendationDebugResultResponse(BaseModel):
    video_id: UUID
    rank: int
    score: float
    reason: str
    impression_count: int
    playback_event_count: int
    view_count: int


class RecommendationDebugResponse(BaseModel):
    request_id: str
    surface: str
    algorithm_version: str
    page: int
    page_size: int
    total_results: int
    results: list[RecommendationDebugResultResponse]
