from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ThumbnailResponse(BaseModel):
    id: UUID
    source: str
    content_type: str
    width: int
    height: int
    selected: bool
    url: str
    created_at: datetime


class ThumbnailListResponse(BaseModel):
    items: list[ThumbnailResponse]
