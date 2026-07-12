"""add recommendation request logging

Revision ID: 20260712_0006
Revises: 20260712_0005
Create Date: 2026-07-12
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260712_0006"
down_revision = "20260712_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("playback_events", sa.Column("request_id", sa.Text(), nullable=True))
    op.create_index("ix_playback_events_request_id", "playback_events", ["request_id"])
    op.add_column("video_views", sa.Column("request_id", sa.Text(), nullable=True))
    op.create_index("ix_video_views_request_id", "video_views", ["request_id"])

    op.create_table(
        "recommendation_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.Text(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("surface", sa.Text(), nullable=False),
        sa.Column("algorithm_version", sa.Text(), nullable=False),
        sa.Column("page", sa.BigInteger(), nullable=False),
        sa.Column("page_size", sa.BigInteger(), nullable=False),
        sa.Column("total_results", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("page >= 1", name="ck_recommendation_requests_page_positive"),
        sa.CheckConstraint("page_size >= 1", name="ck_recommendation_requests_page_size_positive"),
        sa.CheckConstraint("total_results >= 0", name="ck_recommendation_requests_total_results_nonnegative"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_id", name="uq_recommendation_requests_request_id"),
    )
    op.create_index("ix_recommendation_requests_user_created_at", "recommendation_requests", ["user_id", "created_at"])
    op.create_table(
        "recommendation_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("recommendation_request_id", sa.Uuid(), nullable=False),
        sa.Column("video_id", sa.Uuid(), nullable=False),
        sa.Column("rank", sa.BigInteger(), nullable=False),
        sa.Column("score", sa.Numeric(14, 6), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("rank >= 1", name="ck_recommendation_results_rank_positive"),
        sa.ForeignKeyConstraint(["recommendation_request_id"], ["recommendation_requests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("recommendation_request_id", "rank", name="uq_recommendation_results_request_rank"),
        sa.UniqueConstraint("recommendation_request_id", "video_id", name="uq_recommendation_results_request_video"),
    )
    op.create_index("ix_recommendation_results_request_rank", "recommendation_results", ["recommendation_request_id", "rank"])
    op.create_index("ix_recommendation_results_video_id", "recommendation_results", ["video_id"])


def downgrade() -> None:
    op.drop_index("ix_recommendation_results_video_id", table_name="recommendation_results")
    op.drop_index("ix_recommendation_results_request_rank", table_name="recommendation_results")
    op.drop_table("recommendation_results")
    op.drop_index("ix_recommendation_requests_user_created_at", table_name="recommendation_requests")
    op.drop_table("recommendation_requests")
    op.drop_index("ix_video_views_request_id", table_name="video_views")
    op.drop_column("video_views", "request_id")
    op.drop_index("ix_playback_events_request_id", table_name="playback_events")
    op.drop_column("playback_events", "request_id")
