"""add daily analytics metrics

Revision ID: 20260712_0009
Revises: 20260712_0008
Create Date: 2026-07-12
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260712_0009"
down_revision = "20260712_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "video_daily_metrics",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("metric_date", sa.Date(), nullable=False),
        sa.Column("video_id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("impressions", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("views", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("watch_time_seconds", sa.Numeric(14, 3), server_default="0", nullable=False),
        sa.Column("rebuilt_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("impressions >= 0", name="ck_video_daily_metrics_impressions_nonnegative"),
        sa.CheckConstraint("views >= 0", name="ck_video_daily_metrics_views_nonnegative"),
        sa.CheckConstraint("watch_time_seconds >= 0", name="ck_video_daily_metrics_watch_time_nonnegative"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("metric_date", "video_id", name="uq_video_daily_metrics_date_video"),
    )
    op.create_index("ix_video_daily_metrics_owner_date", "video_daily_metrics", ["owner_id", "metric_date"])
    op.create_index("ix_video_daily_metrics_video_date", "video_daily_metrics", ["video_id", "metric_date"])
    op.create_table(
        "creator_daily_metrics",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("metric_date", sa.Date(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("impressions", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("views", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("watch_time_seconds", sa.Numeric(14, 3), server_default="0", nullable=False),
        sa.Column("rebuilt_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("impressions >= 0", name="ck_creator_daily_metrics_impressions_nonnegative"),
        sa.CheckConstraint("views >= 0", name="ck_creator_daily_metrics_views_nonnegative"),
        sa.CheckConstraint("watch_time_seconds >= 0", name="ck_creator_daily_metrics_watch_time_nonnegative"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("metric_date", "owner_id", name="uq_creator_daily_metrics_date_owner"),
    )
    op.create_index("ix_creator_daily_metrics_owner_date", "creator_daily_metrics", ["owner_id", "metric_date"])


def downgrade() -> None:
    op.drop_index("ix_creator_daily_metrics_owner_date", table_name="creator_daily_metrics")
    op.drop_table("creator_daily_metrics")
    op.drop_index("ix_video_daily_metrics_video_date", table_name="video_daily_metrics")
    op.drop_index("ix_video_daily_metrics_owner_date", table_name="video_daily_metrics")
    op.drop_table("video_daily_metrics")
