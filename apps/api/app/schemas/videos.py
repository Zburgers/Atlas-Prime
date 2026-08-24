from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.status import JobStatus, ProcessingStage, RenditionStatus, VideoPrivacy, VideoStatus
from app.schemas.captions import TextTrackResponse


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
    playback_session_id: UUID
    event_id: UUID
    event_type: Literal[
        "player_ready", "play", "pause", "seek", "progress_ping", "buffer_start", "buffer_end", "ended",
        "error", "unsupported", "buffering", "quality_change", "card_click",
    ]
    position_seconds: Decimal | None = Field(default=None, ge=0)
    quality_label: str | None = Field(default=None, max_length=40)
    client_timestamp: datetime | None = None
    request_id: str | None = Field(default=None, max_length=120)


class PlaybackEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID | None
    video_id: UUID
    playback_session_id: UUID
    event_id: UUID
    event_type: str
    position_seconds: Decimal | None
    quality_label: str | None
    client_timestamp: datetime | None
    request_id: str | None
    created_at: datetime


class VideoImpressionCreate(BaseModel):
    surface: str = Field(min_length=1, max_length=40)
    position: int = Field(ge=0)
    request_id: str | None = Field(default=None, max_length=120)


class VideoImpressionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID | None
    video_id: UUID
    surface: str
    position: int
    request_id: str | None
    created_at: datetime


class VideoViewCreate(BaseModel):
    session_id: str = Field(min_length=3, max_length=120)
    position_seconds: Decimal = Field(ge=0)
    request_id: str | None = Field(default=None, max_length=120)


class VideoViewResponse(BaseModel):
    video_id: UUID
    counted: bool
    view_count: int
    threshold_seconds: Decimal


class VideoEngagementResponse(BaseModel):
    video_id: UUID
    liked: bool
    like_count: int
    saved_to_watch_later: bool


class VideoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_id: UUID
    title: str
    description: str | None
    privacy: VideoPrivacy
    status: VideoStatus
    duration_seconds: Decimal | None
    width: int | None
    height: int | None
    video_codec: str | None
    audio_codec: str | None
    source_bitrate: int | None
    view_count: int
    impression_count: int
    like_count: int
    failure_code: str | None
    failure_message: str | None
    created_at: datetime
    updated_at: datetime


class VideoDebugResponse(VideoResponse):
    """Operator-only view of storage-backed video internals."""

    original_storage_key: str | None
    hls_master_storage_key: str | None
    thumbnail_storage_key: str | None


class VideoListItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    channel_id: UUID | None = None
    title: str
    description: str | None
    privacy: VideoPrivacy
    status: VideoStatus
    thumbnail_url: str | None = None
    channel_handle: str | None = None
    channel_display_name: str | None = None
    caption_snippet: str | None = None
    duration_seconds: Decimal | None
    width: int | None
    height: int | None
    view_count: int
    impression_count: int
    like_count: int
    failure_code: str | None
    failure_message: str | None
    created_at: datetime
    updated_at: datetime


class VideoListResponse(BaseModel):
    items: list[VideoListItemResponse]
    total: int
    page: int
    page_size: int


class ProcessingJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    video_id: UUID
    status: JobStatus
    stage: ProcessingStage
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


class ProcessingTimelineResponse(BaseModel):
    items: list[ProcessingJobResponse]


class PlaybackTokenRotationResponse(BaseModel):
    playback_token_version: int


class RenditionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    video_id: UUID
    label: str
    width: int
    height: int
    target_bitrate: int
    video_codec: str | None
    segment_count: int | None
    output_size_bytes: int | None
    status: RenditionStatus
    created_at: datetime


class RenditionDebugResponse(RenditionResponse):
    """Operator-only view of rendition storage internals."""

    playlist_storage_key: str | None


class VideoChapterInput(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    start_seconds: Decimal = Field(ge=0, decimal_places=3)


class VideoChapterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    title: str
    start_seconds: Decimal


class VideoChapterReplace(BaseModel):
    items: list[VideoChapterInput] = Field(max_length=100)


class VideoChapterListResponse(BaseModel):
    items: list[VideoChapterResponse]


class PlaybackResponse(BaseModel):
    video_id: UUID
    status: VideoStatus
    master_playlist_url: str | None
    thumbnail_url: str | None
    renditions: list[RenditionResponse]
    text_tracks: list[TextTrackResponse] = []
    chapters: list[VideoChapterResponse] = []


class VideoUploadResponse(BaseModel):
    video: VideoResponse
    processing_job: ProcessingJobResponse
    size_bytes: int
    content_type: str


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
    video: VideoDebugResponse
    renditions: list[RenditionDebugResponse]
    processing_jobs: list[ProcessingJobResponse]
    recent_playback_events: list[PlaybackEventResponse]


class AdminOpsResponse(BaseModel):
    status: Literal["ok", "degraded"]
    api: dict[str, object]
    worker: dict[str, object]
    redis: dict[str, object]
