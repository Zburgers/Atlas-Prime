from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.db.base import Base
from app.domain.status import (
    CANONICAL_VIDEO_STATUS_VALUES,
    PRIVACY_VALUES,
    JobStatus,
    RenditionStatus,
    VideoPrivacy,
    VideoStatus,
)


def _values_sql(values: list[str]) -> str:
    return "(" + ", ".join(f"'{value}'" for value in values) + ")"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str | None] = mapped_column(Text)
    clerk_user_id: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    videos: Mapped[list[Video]] = relationship(back_populates="owner", cascade="all, delete-orphan")


Index("ix_users_lower_email", func.lower(User.email))


class Video(Base):
    __tablename__ = "videos"
    __table_args__ = (
        CheckConstraint(f"privacy in {_values_sql(PRIVACY_VALUES)}", name="ck_videos_privacy"),
        CheckConstraint(f"status in {_values_sql(CANONICAL_VIDEO_STATUS_VALUES)}", name="ck_videos_status"),
        CheckConstraint("duration_seconds is null or duration_seconds >= 0", name="ck_videos_duration_nonnegative"),
        CheckConstraint("width is null or width > 0", name="ck_videos_width_positive"),
        CheckConstraint("height is null or height > 0", name="ck_videos_height_positive"),
        CheckConstraint("source_bitrate is null or source_bitrate > 0", name="ck_videos_source_bitrate_positive"),
        Index("ix_videos_owner_created_at", "owner_id", "created_at"),
        Index("ix_videos_owner_status", "owner_id", "status"),
        Index("ix_videos_public_ready", "privacy", "status", postgresql_where="status = 'ready'"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    privacy: Mapped[str] = mapped_column(Text, nullable=False, default=VideoPrivacy.PRIVATE.value, server_default=VideoPrivacy.PRIVATE.value)
    status: Mapped[str] = mapped_column(Text, nullable=False, default=VideoStatus.DRAFT.value, server_default=VideoStatus.DRAFT.value)
    original_storage_key: Mapped[str | None] = mapped_column(Text)
    hls_master_storage_key: Mapped[str | None] = mapped_column(Text)
    thumbnail_storage_key: Mapped[str | None] = mapped_column(Text)
    duration_seconds: Mapped[Decimal | None] = mapped_column(Numeric(10, 3))
    width: Mapped[int | None]
    height: Mapped[int | None]
    video_codec: Mapped[str | None] = mapped_column(Text)
    audio_codec: Mapped[str | None] = mapped_column(Text)
    source_bitrate: Mapped[int | None]
    failure_code: Mapped[str | None] = mapped_column(Text)
    failure_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    owner: Mapped[User] = relationship(back_populates="videos")
    renditions: Mapped[list[VideoRendition]] = relationship(back_populates="video", cascade="all, delete-orphan")
    processing_jobs: Mapped[list[VideoProcessingJob]] = relationship(back_populates="video", cascade="all, delete-orphan")


class VideoRendition(Base):
    __tablename__ = "video_renditions"
    __table_args__ = (
        CheckConstraint(
            f"status in {_values_sql([status.value for status in RenditionStatus])}",
            name="ck_video_renditions_status",
        ),
        CheckConstraint("width > 0", name="ck_video_renditions_width_positive"),
        CheckConstraint("height > 0", name="ck_video_renditions_height_positive"),
        CheckConstraint("target_bitrate > 0", name="ck_video_renditions_target_bitrate_positive"),
        UniqueConstraint("video_id", "label", name="uq_video_renditions_video_label"),
        Index("ix_video_renditions_video_id", "video_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    width: Mapped[int] = mapped_column(nullable=False)
    height: Mapped[int] = mapped_column(nullable=False)
    target_bitrate: Mapped[int] = mapped_column(nullable=False)
    playlist_storage_key: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, default=RenditionStatus.PENDING.value, server_default=RenditionStatus.PENDING.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    video: Mapped[Video] = relationship(back_populates="renditions")


class VideoProcessingJob(Base):
    __tablename__ = "video_processing_jobs"
    __table_args__ = (
        CheckConstraint(f"status in {_values_sql([status.value for status in JobStatus])}", name="ck_video_processing_jobs_status"),
        CheckConstraint("attempt_count >= 0", name="ck_video_processing_jobs_attempt_count_nonnegative"),
        Index("ix_video_processing_jobs_video_created_at", "video_id", "created_at"),
        Index("ix_video_processing_jobs_status_created_at", "status", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default=JobStatus.QUEUED.value, server_default=JobStatus.QUEUED.value)
    attempt_count: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    worker_id: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    video: Mapped[Video] = relationship(back_populates="processing_jobs")


class PlaybackEvent(Base):
    __tablename__ = "playback_events"
    __table_args__ = (
        CheckConstraint("position_seconds is null or position_seconds >= 0", name="ck_playback_events_position_nonnegative"),
        Index("ix_playback_events_video_created_at", "video_id", "created_at"),
        Index("ix_playback_events_user_created_at", "user_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    video_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    position_seconds: Mapped[Decimal | None] = mapped_column(Numeric(10, 3))
    quality_label: Mapped[str | None] = mapped_column(Text)
    client_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
