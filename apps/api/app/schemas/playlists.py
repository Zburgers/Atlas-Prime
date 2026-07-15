from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.videos import VideoListItemResponse


class PlaylistCreate(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    description: str | None = Field(default=None, max_length=2000)
    privacy: str = Field(default="private", pattern="^(private|public)$")


class PlaylistItemCreate(BaseModel):
    video_id: UUID


class PlaylistItemResponse(BaseModel):
    id: UUID
    position: int
    created_at: datetime
    video: VideoListItemResponse


class PlaylistResponse(BaseModel):
    id: UUID
    owner_id: UUID
    title: str
    description: str | None
    privacy: str
    created_at: datetime
    updated_at: datetime
    items: list[PlaylistItemResponse]
