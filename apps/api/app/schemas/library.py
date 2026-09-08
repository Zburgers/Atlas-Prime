from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.videos import VideoListItemResponse


class WatchHistoryItemResponse(BaseModel):
    id: UUID
    position_seconds: float | None
    watched_at: datetime
    video: VideoListItemResponse


class WatchHistoryResponse(BaseModel):
    items: list[WatchHistoryItemResponse]
