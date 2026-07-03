"""add impressions and views

Revision ID: 20260702_0003
Revises: 20260702_0002
Create Date: 2026-07-02
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260702_0003"
down_revision = "20260702_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("videos", sa.Column("view_count", sa.BigInteger(), server_default="0", nullable=False))
    op.add_column("videos", sa.Column("impression_count", sa.BigInteger(), server_default="0", nullable=False))
    op.create_check_constraint("ck_videos_view_count_nonnegative", "videos", "view_count >= 0")
    op.create_check_constraint("ck_videos_impression_count_nonnegative", "videos", "impression_count >= 0")

    op.create_table(
        "video_impressions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("video_id", sa.Uuid(), nullable=False),
        sa.Column("surface", sa.Text(), nullable=False),
        sa.Column("position", sa.BigInteger(), nullable=False),
        sa.Column("request_id", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("position >= 0", name="ck_video_impressions_position_nonnegative"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_video_impressions_video_created_at", "video_impressions", ["video_id", "created_at"])
    op.create_index("ix_video_impressions_request_id", "video_impressions", ["request_id"])

    op.create_table(
        "video_views",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("video_id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Text(), nullable=False),
        sa.Column("position_seconds", sa.Numeric(10, 3), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("position_seconds >= 0", name="ck_video_views_position_nonnegative"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("video_id", "session_id", name="uq_video_views_video_session"),
    )
    op.create_index("ix_video_views_video_created_at", "video_views", ["video_id", "created_at"])
    op.create_index("ix_video_views_user_created_at", "video_views", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_video_views_user_created_at", table_name="video_views")
    op.drop_index("ix_video_views_video_created_at", table_name="video_views")
    op.drop_table("video_views")
    op.drop_index("ix_video_impressions_request_id", table_name="video_impressions")
    op.drop_index("ix_video_impressions_video_created_at", table_name="video_impressions")
    op.drop_table("video_impressions")
    op.drop_constraint("ck_videos_impression_count_nonnegative", "videos", type_="check")
    op.drop_constraint("ck_videos_view_count_nonnegative", "videos", type_="check")
    op.drop_column("videos", "impression_count")
    op.drop_column("videos", "view_count")
