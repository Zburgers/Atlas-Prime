from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


TargetType = Literal["video", "comment"]
ModerationActionName = Literal["remove", "restore", "limit"]


class ContentReportCreate(BaseModel):
    target_type: TargetType
    target_id: UUID
    reason: str = Field(min_length=1, max_length=120)
    details: str | None = Field(default=None, max_length=2000)


class ContentReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    reporter_user_id: UUID | None
    target_type: TargetType
    target_id: UUID
    reason: str
    details: str | None
    status: Literal["open", "actioned", "dismissed"]
    created_at: datetime


class ContentReportListResponse(BaseModel):
    items: list[ContentReportResponse]
    total: int


class ModerationActionCreate(BaseModel):
    action: ModerationActionName
    reason: str | None = Field(default=None, max_length=2000)


class ModerationActionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    actor_user_id: UUID | None
    target_type: TargetType
    target_id: UUID
    action: ModerationActionName
    reason: str | None
    created_at: datetime


class ModerationActionResult(BaseModel):
    report: ContentReportResponse
    action: ModerationActionResponse


class AuditLogEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    actor_user_id: UUID | None
    action: str
    target_type: str
    target_id: UUID
    metadata_json: dict[str, object]
    created_at: datetime


class AuditLogListResponse(BaseModel):
    items: list[AuditLogEntryResponse]
