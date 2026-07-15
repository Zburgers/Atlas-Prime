from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, Index, Numeric, Text, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.db.base import Base
from app.domain.status import (
    CANONICAL_VIDEO_STATUS_VALUES,
    MODERATION_STATUS_VALUES,
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
    subscriptions: Mapped[list[ChannelSubscription]] = relationship(back_populates="channel", cascade="all, delete-orphan")


class Video(Base):
    __tablename__ = "videos"
    __table_args__ = (
        CheckConstraint(f"privacy in {_values_sql(PRIVACY_VALUES)}", name="ck_videos_privacy"),
        CheckConstraint(f"status in {_values_sql(CANONICAL_VIDEO_STATUS_VALUES)}", name="ck_videos_status"),
        CheckConstraint(f"moderation_status in {_values_sql(MODERATION_STATUS_VALUES)}", name="ck_videos_moderation_status"),
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
    moderation_status: Mapped[str] = mapped_column(Text, nullable=False, default="approved", server_default="approved")
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
    recommendation_results: Mapped[list[RecommendationResult]] = relationship(back_populates="video", cascade="all, delete-orphan")
    thumbnails: Mapped[list[VideoThumbnail]] = relationship(back_populates="video", cascade="all, delete-orphan")
    text_tracks: Mapped[list[VideoTextTrack]] = relationship(back_populates="video", cascade="all, delete-orphan")


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
    video_codec: Mapped[str | None] = mapped_column(Text)
    segment_count: Mapped[int | None]
    output_size_bytes: Mapped[int | None]
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
        Index("ix_playback_events_request_id", "request_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    video_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    position_seconds: Mapped[Decimal | None] = mapped_column(Numeric(10, 3))
    quality_label: Mapped[str | None] = mapped_column(Text)
    client_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    request_id: Mapped[str | None] = mapped_column(Text)
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
        Index("ix_video_views_request_id", "request_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    video_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    session_id: Mapped[str] = mapped_column(Text, nullable=False)
    position_seconds: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    request_id: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    video: Mapped[Video] = relationship(back_populates="views")


class VideoDailyMetric(Base):
    __tablename__ = "video_daily_metrics"
    __table_args__ = (
        CheckConstraint("impressions >= 0", name="ck_video_daily_metrics_impressions_nonnegative"),
        CheckConstraint("views >= 0", name="ck_video_daily_metrics_views_nonnegative"),
        CheckConstraint("watch_time_seconds >= 0", name="ck_video_daily_metrics_watch_time_nonnegative"),
        UniqueConstraint("metric_date", "video_id", name="uq_video_daily_metrics_date_video"),
        Index("ix_video_daily_metrics_owner_date", "owner_id", "metric_date"),
        Index("ix_video_daily_metrics_video_date", "video_id", "metric_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    metric_date: Mapped[date] = mapped_column(nullable=False)
    video_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    impressions: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    views: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    watch_time_seconds: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False, default=0, server_default="0")
    rebuilt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class CreatorDailyMetric(Base):
    __tablename__ = "creator_daily_metrics"
    __table_args__ = (
        CheckConstraint("impressions >= 0", name="ck_creator_daily_metrics_impressions_nonnegative"),
        CheckConstraint("views >= 0", name="ck_creator_daily_metrics_views_nonnegative"),
        CheckConstraint("watch_time_seconds >= 0", name="ck_creator_daily_metrics_watch_time_nonnegative"),
        UniqueConstraint("metric_date", "owner_id", name="uq_creator_daily_metrics_date_owner"),
        Index("ix_creator_daily_metrics_owner_date", "owner_id", "metric_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    metric_date: Mapped[date] = mapped_column(nullable=False)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    impressions: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    views: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    watch_time_seconds: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False, default=0, server_default="0")
    rebuilt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class VideoThumbnail(Base):
    __tablename__ = "video_thumbnails"
    __table_args__ = (
        CheckConstraint("source in ('generated', 'custom')", name="ck_video_thumbnails_source"),
        CheckConstraint("width > 0", name="ck_video_thumbnails_width_positive"),
        CheckConstraint("height > 0", name="ck_video_thumbnails_height_positive"),
        UniqueConstraint("video_id", "storage_key", name="uq_video_thumbnails_video_storage_key"),
        Index("ix_video_thumbnails_video_created_at", "video_id", "created_at"),
        Index(
            "uq_video_thumbnails_selected_per_video",
            "video_id",
            unique=True,
            postgresql_where=text("selected"),
            sqlite_where=text("selected"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(Text, nullable=False)
    width: Mapped[int] = mapped_column(nullable=False)
    height: Mapped[int] = mapped_column(nullable=False)
    selected: Mapped[bool] = mapped_column(nullable=False, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    video: Mapped[Video] = relationship(back_populates="thumbnails")


class VideoTextTrack(Base):
    __tablename__ = "video_text_tracks"
    __table_args__ = (
        CheckConstraint("kind in ('captions')", name="ck_video_text_tracks_kind"),
        UniqueConstraint("video_id", "language", "kind", name="uq_video_text_tracks_video_language_kind"),
        Index("ix_video_text_tracks_video_created_at", "video_id", "created_at"),
        Index(
            "uq_video_text_tracks_default_per_video",
            "video_id",
            unique=True,
            postgresql_where=text("is_default"),
            sqlite_where=text("is_default"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    language: Mapped[str] = mapped_column(Text, nullable=False)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[str] = mapped_column(Text, nullable=False, default="captions", server_default="captions")
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(Text, nullable=False, default="text/vtt", server_default="text/vtt")
    is_default: Mapped[bool] = mapped_column(nullable=False, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    video: Mapped[Video] = relationship(back_populates="text_tracks")


class RecommendationRequest(Base):
    __tablename__ = "recommendation_requests"
    __table_args__ = (
        CheckConstraint("page >= 1", name="ck_recommendation_requests_page_positive"),
        CheckConstraint("page_size >= 1", name="ck_recommendation_requests_page_size_positive"),
        CheckConstraint("total_results >= 0", name="ck_recommendation_requests_total_results_nonnegative"),
        UniqueConstraint("request_id", name="uq_recommendation_requests_request_id"),
        Index("ix_recommendation_requests_user_created_at", "user_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id: Mapped[str] = mapped_column(Text, nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    surface: Mapped[str] = mapped_column(Text, nullable=False)
    algorithm_version: Mapped[str] = mapped_column(Text, nullable=False)
    page: Mapped[int] = mapped_column(nullable=False)
    page_size: Mapped[int] = mapped_column(nullable=False)
    total_results: Mapped[int] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    results: Mapped[list[RecommendationResult]] = relationship(back_populates="recommendation_request", cascade="all, delete-orphan")


class RecommendationResult(Base):
    __tablename__ = "recommendation_results"
    __table_args__ = (
        CheckConstraint("rank >= 1", name="ck_recommendation_results_rank_positive"),
        UniqueConstraint("recommendation_request_id", "rank", name="uq_recommendation_results_request_rank"),
        UniqueConstraint("recommendation_request_id", "video_id", name="uq_recommendation_results_request_video"),
        Index("ix_recommendation_results_request_rank", "recommendation_request_id", "rank"),
        Index("ix_recommendation_results_video_id", "video_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recommendation_request_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("recommendation_requests.id", ondelete="CASCADE"), nullable=False
    )
    video_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    rank: Mapped[int] = mapped_column(nullable=False)
    score: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    recommendation_request: Mapped[RecommendationRequest] = relationship(back_populates="results")
    video: Mapped[Video] = relationship(back_populates="recommendation_results")


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


class ChannelSubscription(Base):
    __tablename__ = "channel_subscriptions"
    __table_args__ = (UniqueConstraint("user_id", "channel_id", name="uq_channel_subscriptions_user_channel"), Index("ix_channel_subscriptions_user_created_at", "user_id", "created_at"))

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    channel_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("channels.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    channel: Mapped[Channel] = relationship(back_populates="subscriptions")


class WatchHistory(Base):
    __tablename__ = "watch_history"
    __table_args__ = (UniqueConstraint("user_id", "video_id", name="uq_watch_history_user_video"), Index("ix_watch_history_user_watched_at", "user_id", "watched_at"))

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    video_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    position_seconds: Mapped[Decimal | None] = mapped_column(Numeric(10, 3))
    watched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    video: Mapped[Video] = relationship()


class Playlist(Base):
    __tablename__ = "playlists"
    __table_args__ = (
        CheckConstraint("privacy in ('private', 'public')", name="ck_playlists_privacy"),
        Index("ix_playlists_owner_created_at", "owner_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    privacy: Mapped[str] = mapped_column(Text, nullable=False, default="private", server_default="private")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    items: Mapped[list[PlaylistItem]] = relationship(back_populates="playlist", cascade="all, delete-orphan")


class PlaylistItem(Base):
    __tablename__ = "playlist_items"
    __table_args__ = (
        UniqueConstraint("playlist_id", "video_id", name="uq_playlist_items_playlist_video"),
        UniqueConstraint("playlist_id", "position", name="uq_playlist_items_playlist_position"),
        Index("ix_playlist_items_playlist_position", "playlist_id", "position"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    playlist_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("playlists.id", ondelete="CASCADE"), nullable=False)
    video_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    position: Mapped[int] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    playlist: Mapped[Playlist] = relationship(back_populates="items")
    video: Mapped[Video] = relationship()


class VideoComment(Base):
    __tablename__ = "video_comments"
    __table_args__ = (
        CheckConstraint("length(body) >= 1", name="ck_video_comments_body_min_length"),
        CheckConstraint(f"moderation_status in {_values_sql(MODERATION_STATUS_VALUES)}", name="ck_video_comments_moderation_status"),
        Index("ix_video_comments_video_created_at", "video_id", "created_at"),
        Index("ix_video_comments_user_created_at", "user_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    body: Mapped[str] = mapped_column(Text, nullable=False)
    moderation_status: Mapped[str] = mapped_column(Text, nullable=False, default="approved", server_default="approved")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    video: Mapped[Video] = relationship(back_populates="comments")
    user: Mapped[User | None] = relationship()


class ContentReport(Base):
    __tablename__ = "content_reports"
    __table_args__ = (
        CheckConstraint("target_type in ('video', 'comment')", name="ck_content_reports_target_type"),
        CheckConstraint("status in ('open', 'actioned', 'dismissed')", name="ck_content_reports_status"),
        Index("ix_content_reports_status_created_at", "status", "created_at"),
        Index("ix_content_reports_target", "target_type", "target_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reporter_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    target_type: Mapped[str] = mapped_column(Text, nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="open", server_default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ModerationAction(Base):
    __tablename__ = "moderation_actions"
    __table_args__ = (
        CheckConstraint("target_type in ('video', 'comment')", name="ck_moderation_actions_target_type"),
        CheckConstraint("action in ('remove', 'restore', 'limit')", name="ck_moderation_actions_action"),
        Index("ix_moderation_actions_target_created_at", "target_type", "target_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    target_type: Mapped[str] = mapped_column(Text, nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class AuditLogEntry(Base):
    __tablename__ = "audit_log_entries"
    __table_args__ = (
        Index("ix_audit_log_entries_target_created_at", "target_type", "target_id", "created_at"),
        Index("ix_audit_log_entries_actor_created_at", "actor_user_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(Text, nullable=False)
    target_type: Mapped[str] = mapped_column(Text, nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
