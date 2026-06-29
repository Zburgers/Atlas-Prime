from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.status import JobStatus, RenditionStatus, VideoPrivacy, VideoStatus


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str | None
    clerk_user_id: str
    created_at: datetime


class VideoCreate(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    description: str | None = Field(default=None, max_length=5000)


class VideoUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=180)
    description: str | None = Field(default=None, max_length=5000)
    privacy: VideoPrivacy | None = None


class PlaybackEventCreate(BaseModel):
    event_type: Literal["player_ready", "play", "pause", "error", "unsupported", "buffering", "quality_change"]
    position_seconds: Decimal | None = Field(default=None, ge=0)
    quality_label: str | None = Field(default=None, max_length=40)
    client_timestamp: datetime | None = None


class PlaybackEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID | None
    video_id: UUID
    event_type: str
    position_seconds: Decimal | None
    quality_label: str | None
    client_timestamp: datetime | None
    created_at: datetime


class VideoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_id: UUID
    title: str
    description: str | None
    privacy: VideoPrivacy
    status: VideoStatus
    original_storage_key: str | None
    hls_master_storage_key: str | None
    thumbnail_storage_key: str | None
    duration_seconds: Decimal | None
    width: int | None
    height: int | None
    video_codec: str | None
    audio_codec: str | None
    source_bitrate: int | None
    failure_code: str | None
    failure_message: str | None
    created_at: datetime
    updated_at: datetime


class VideoListResponse(BaseModel):
    items: list[VideoResponse]
    total: int
    page: int
    page_size: int


class ProcessingJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    video_id: UUID
    status: JobStatus
    attempt_count: int
    worker_id: str | None
    started_at: datetime | None
    finished_at: datetime | None
    error_code: str | None
    error_message: str | None
    created_at: datetime


class ProcessingStatusResponse(BaseModel):
    video_id: UUID
    video_status: VideoStatus
    latest_job: ProcessingJobResponse | None
    failure_code: str | None
    failure_message: str | None


class RenditionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    video_id: UUID
    label: str
    width: int
    height: int
    target_bitrate: int
    playlist_storage_key: str | None
    status: RenditionStatus
    created_at: datetime


class PlaybackResponse(BaseModel):
    video_id: UUID
    status: VideoStatus
    master_playlist_url: str | None
    thumbnail_url: str | None
    renditions: list[RenditionResponse]


class VideoUploadResponse(BaseModel):
    video: VideoResponse
    processing_job: ProcessingJobResponse
    storage_key: str
    size_bytes: int
    content_type: str
    celery_task_id: str


class ErrorResponse(BaseModel):
    error: str
    message: str
    details: dict[str, object] | None = None


class AdminJobResponse(ProcessingJobResponse):
    video_title: str | None = None
    video_status: VideoStatus | None = None
    video_failure_code: str | None = None
    video_failure_message: str | None = None


class AdminVideoDebugResponse(BaseModel):
    video: VideoResponse
    renditions: list[RenditionResponse]
    processing_jobs: list[ProcessingJobResponse]
    recent_playback_events: list[PlaybackEventResponse]


class AdminOpsResponse(BaseModel):
    status: Literal["ok", "degraded"]
    api: dict[str, object]
    worker: dict[str, object]
    redis: dict[str, object]
