"""core video domain

Revision ID: 20260628_0001
Revises:
Create Date: 2026-06-28
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260628_0001"
down_revision = None
branch_labels = None
depends_on = None

VIDEO_STATUSES = (
    "draft",
    "uploading",
    "uploaded",
    "queued",
    "probing",
    "processing",
    "ready",
    "failed",
)
PRIVACY_VALUES = ("private", "public", "unlisted")
JOB_STATUSES = ("queued", "running", "succeeded", "failed", "canceled")
RENDITION_STATUSES = ("pending", "processing", "ready", "failed")


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.Text(), nullable=True),
        sa.Column("clerk_user_id", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("clerk_user_id", name="uq_users_clerk_user_id"),
    )
    op.create_index("ix_users_lower_email", "users", [sa.text("lower(email)")])

    op.create_table(
        "videos",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("privacy", sa.Text(), server_default="private", nullable=False),
        sa.Column("status", sa.Text(), server_default="draft", nullable=False),
        sa.Column("original_storage_key", sa.Text(), nullable=True),
        sa.Column("hls_master_storage_key", sa.Text(), nullable=True),
        sa.Column("thumbnail_storage_key", sa.Text(), nullable=True),
        sa.Column("duration_seconds", sa.Numeric(10, 3), nullable=True),
        sa.Column("width", sa.BigInteger(), nullable=True),
        sa.Column("height", sa.BigInteger(), nullable=True),
        sa.Column("video_codec", sa.Text(), nullable=True),
        sa.Column("audio_codec", sa.Text(), nullable=True),
        sa.Column("source_bitrate", sa.BigInteger(), nullable=True),
        sa.Column("failure_code", sa.Text(), nullable=True),
        sa.Column("failure_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(f"privacy in {PRIVACY_VALUES}", name="ck_videos_privacy"),
        sa.CheckConstraint(f"status in {VIDEO_STATUSES}", name="ck_videos_status"),
        sa.CheckConstraint("duration_seconds is null or duration_seconds >= 0", name="ck_videos_duration_nonnegative"),
        sa.CheckConstraint("width is null or width > 0", name="ck_videos_width_positive"),
        sa.CheckConstraint("height is null or height > 0", name="ck_videos_height_positive"),
        sa.CheckConstraint("source_bitrate is null or source_bitrate > 0", name="ck_videos_source_bitrate_positive"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_videos_owner_created_at", "videos", ["owner_id", "created_at"])
    op.create_index("ix_videos_owner_status", "videos", ["owner_id", "status"])
    op.create_index("ix_videos_public_ready", "videos", ["privacy", "status"], postgresql_where=sa.text("status = 'ready'"))

    op.create_table(
        "video_renditions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("video_id", sa.Uuid(), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("width", sa.BigInteger(), nullable=False),
        sa.Column("height", sa.BigInteger(), nullable=False),
        sa.Column("target_bitrate", sa.BigInteger(), nullable=False),
        sa.Column("playlist_storage_key", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), server_default="pending", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(f"status in {RENDITION_STATUSES}", name="ck_video_renditions_status"),
        sa.CheckConstraint("width > 0", name="ck_video_renditions_width_positive"),
        sa.CheckConstraint("height > 0", name="ck_video_renditions_height_positive"),
        sa.CheckConstraint("target_bitrate > 0", name="ck_video_renditions_target_bitrate_positive"),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("video_id", "label", name="uq_video_renditions_video_label"),
    )
    op.create_index("ix_video_renditions_video_id", "video_renditions", ["video_id"])

    op.create_table(
        "video_processing_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("video_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.Text(), server_default="queued", nullable=False),
        sa.Column("attempt_count", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("worker_id", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(f"status in {JOB_STATUSES}", name="ck_video_processing_jobs_status"),
        sa.CheckConstraint("attempt_count >= 0", name="ck_video_processing_jobs_attempt_count_nonnegative"),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_video_processing_jobs_video_created_at", "video_processing_jobs", ["video_id", "created_at"])
    op.create_index("ix_video_processing_jobs_status_created_at", "video_processing_jobs", ["status", "created_at"])

    op.create_table(
        "playback_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("video_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("position_seconds", sa.Numeric(10, 3), nullable=True),
        sa.Column("quality_label", sa.Text(), nullable=True),
        sa.Column("client_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("position_seconds is null or position_seconds >= 0", name="ck_playback_events_position_nonnegative"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_playback_events_video_created_at", "playback_events", ["video_id", "created_at"])
    op.create_index("ix_playback_events_user_created_at", "playback_events", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_playback_events_user_created_at", table_name="playback_events")
    op.drop_index("ix_playback_events_video_created_at", table_name="playback_events")
    op.drop_table("playback_events")
    op.drop_index("ix_video_processing_jobs_status_created_at", table_name="video_processing_jobs")
    op.drop_index("ix_video_processing_jobs_video_created_at", table_name="video_processing_jobs")
    op.drop_table("video_processing_jobs")
    op.drop_index("ix_video_renditions_video_id", table_name="video_renditions")
    op.drop_table("video_renditions")
    op.drop_index("ix_videos_public_ready", table_name="videos")
    op.drop_index("ix_videos_owner_status", table_name="videos")
    op.drop_index("ix_videos_owner_created_at", table_name="videos")
    op.drop_table("videos")
    op.drop_index("ix_users_lower_email", table_name="users")
    op.drop_table("users")
