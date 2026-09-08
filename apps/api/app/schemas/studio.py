from __future__ import annotations

from pydantic import BaseModel, Field

from app.domain.status import VideoPrivacy
from app.schemas.videos import VideoListItemResponse


class StudioVideoListResponse(BaseModel):
    items: list[VideoListItemResponse]
    total: int
    page: int
    page_size: int


class StudioVideoUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=180)
    description: str | None = Field(default=None, max_length=5000)
    privacy: VideoPrivacy | None = None
