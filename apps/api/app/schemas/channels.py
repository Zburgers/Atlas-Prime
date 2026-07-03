from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.videos import VideoListItemResponse


class ChannelUpdate(BaseModel):
    handle: str | None = Field(default=None, min_length=1, max_length=80)
    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=1000)


class ChannelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_user_id: UUID
    handle: str
    display_name: str
    description: str | None
    avatar_storage_key: str | None
    banner_storage_key: str | None
    created_at: datetime
    updated_at: datetime


class PublicChannelResponse(ChannelResponse):
    videos: list[VideoListItemResponse]
