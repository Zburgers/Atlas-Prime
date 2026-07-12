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

    channel: Mapped[Channel | None] = relationship(back_populates="owner", cascade="all, delete-orphan", uselist=False)
    videos: Mapped[list[Video]] = relationship(back_populates="owner", cascade="all, delete-orphan")


Index("ix_users_lower_email", func.lower(User.email))


class Channel(Base):
    __tablename__ = "channels"
    __table_args__ = (
        CheckConstraint("length(handle) >= 3", name="ck_channels_handle_min_length"),
        CheckConstraint("length(display_name) >= 1", name="ck_channels_display_name_min_length"),
        UniqueConstraint("owner_user_id", name="uq_channels_owner_user_id"),
        UniqueConstraint("handle", name="uq_channels_handle"),
        Index("ix_channels_handle", "handle"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    handle: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    avatar_storage_key: Mapped[str | None] = mapped_column(Text)
    banner_storage_key: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    owner: Mapped[User] = relationship(back_populates="channel")
    videos: Mapped[list[Video]] = relationship(back_populates="channel")


class Video(Base):
    __tablename__ = "videos"
    __table_args__ = (
        CheckConstraint(f"privacy in {_values_sql(PRIVACY_VALUES)}", name="ck_videos_privacy"),
        CheckConstraint(f"status in {_values_sql(CANONICAL_VIDEO_STATUS_VALUES)}", name="ck_videos_status"),
        CheckConstraint("duration_seconds is null or duration_seconds >= 0", name="ck_videos_duration_nonnegative"),
        CheckConstraint("width is null or width > 0", name="ck_videos_width_positive"),
        CheckConstraint("height is null or height > 0", name="ck_videos_height_positive"),
        CheckConstraint("source_bitrate is null or source_bitrate > 0", name="ck_videos_source_bitrate_positive"),
        CheckConstraint("view_count >= 0", name="ck_videos_view_count_nonnegative"),
        CheckConstraint("impression_count >= 0", name="ck_videos_impression_count_nonnegative"),
        CheckConstraint("like_count >= 0", name="ck_videos_like_count_nonnegative"),
        Index("ix_videos_owner_created_at", "owner_id", "created_at"),
        Index("ix_videos_owner_status", "owner_id", "status"),
        Index("ix_videos_channel_created_at", "channel_id", "created_at"),
        Index("ix_videos_public_ready", "privacy", "status", postgresql_where="status = 'ready'"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    channel_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("channels.id", ondelete="SET NULL"))
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
    view_count: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    impression_count: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    like_count: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    failure_code: Mapped[str | None] = mapped_column(Text)
    failure_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    owner: Mapped[User] = relationship(back_populates="videos")
    channel: Mapped[Channel | None] = relationship(back_populates="videos")
    renditions: Mapped[list[VideoRendition]] = relationship(back_populates="video", cascade="all, delete-orphan")
    processing_jobs: Mapped[list[VideoProcessingJob]] = relationship(back_populates="video", cascade="all, delete-orphan")
    impressions: Mapped[list[VideoImpression]] = relationship(back_populates="video", cascade="all, delete-orphan")
    views: Mapped[list[VideoView]] = relationship(back_populates="video", cascade="all, delete-orphan")
    reactions: Mapped[list[VideoReaction]] = relationship(back_populates="video", cascade="all, delete-orphan")
    saves: Mapped[list[VideoSave]] = relationship(back_populates="video", cascade="all, delete-orphan")
    comments: Mapped[list[VideoComment]] = relationship(back_populates="video", cascade="all, delete-orphan")


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


class VideoImpression(Base):
    __tablename__ = "video_impressions"
    __table_args__ = (
        CheckConstraint("position >= 0", name="ck_video_impressions_position_nonnegative"),
        Index("ix_video_impressions_video_created_at", "video_id", "created_at"),
        Index("ix_video_impressions_request_id", "request_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    video_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    surface: Mapped[str] = mapped_column(Text, nullable=False)
    position: Mapped[int] = mapped_column(nullable=False)
    request_id: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    video: Mapped[Video] = relationship(back_populates="impressions")


class VideoView(Base):
    __tablename__ = "video_views"
    __table_args__ = (
        CheckConstraint("position_seconds >= 0", name="ck_video_views_position_nonnegative"),
        UniqueConstraint("video_id", "session_id", name="uq_video_views_video_session"),
        Index("ix_video_views_video_created_at", "video_id", "created_at"),
        Index("ix_video_views_user_created_at", "user_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    video_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    session_id: Mapped[str] = mapped_column(Text, nullable=False)
    position_seconds: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    video: Mapped[Video] = relationship(back_populates="views")


class VideoReaction(Base):
    __tablename__ = "video_reactions"
    __table_args__ = (
        CheckConstraint("reaction_type in ('like')", name="ck_video_reactions_type"),
        UniqueConstraint("user_id", "video_id", "reaction_type", name="uq_video_reactions_user_video_type"),
        Index("ix_video_reactions_video_created_at", "video_id", "created_at"),
        Index("ix_video_reactions_user_created_at", "user_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    video_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    reaction_type: Mapped[str] = mapped_column(Text, nullable=False, default="like", server_default="like")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    video: Mapped[Video] = relationship(back_populates="reactions")


class VideoSave(Base):
    __tablename__ = "video_saves"
    __table_args__ = (
        UniqueConstraint("user_id", "video_id", name="uq_video_saves_user_video"),
        Index("ix_video_saves_video_created_at", "video_id", "created_at"),
        Index("ix_video_saves_user_created_at", "user_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    video_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    video: Mapped[Video] = relationship(back_populates="saves")


class VideoComment(Base):
    __tablename__ = "video_comments"
    __table_args__ = (
        CheckConstraint("length(body) >= 1", name="ck_video_comments_body_min_length"),
        Index("ix_video_comments_video_created_at", "video_id", "created_at"),
        Index("ix_video_comments_user_created_at", "user_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    video: Mapped[Video] = relationship(back_populates="comments")
    user: Mapped[User | None] = relationship()
