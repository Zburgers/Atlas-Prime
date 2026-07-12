from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class TextTrackResponse(BaseModel):
    id: UUID
    language: str
    label: str
    kind: str
    default: bool
    url: str
    created_at: datetime


class TextTrackListResponse(BaseModel):
    items: list[TextTrackResponse]
