"""add video reactions and saves

Revision ID: 20260703_0004
Revises: 20260702_0003
Create Date: 2026-07-03
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260703_0004"
down_revision = "20260702_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("videos", sa.Column("like_count", sa.BigInteger(), server_default="0", nullable=False))
    op.create_check_constraint("ck_videos_like_count_nonnegative", "videos", "like_count >= 0")

    op.create_table(
        "video_reactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("video_id", sa.Uuid(), nullable=False),
        sa.Column("reaction_type", sa.Text(), server_default="like", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("reaction_type in ('like')", name="ck_video_reactions_type"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "video_id", "reaction_type", name="uq_video_reactions_user_video_type"),
    )
    op.create_index("ix_video_reactions_video_created_at", "video_reactions", ["video_id", "created_at"])
    op.create_index("ix_video_reactions_user_created_at", "video_reactions", ["user_id", "created_at"])

    op.create_table(
        "video_saves",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("video_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "video_id", name="uq_video_saves_user_video"),
    )
    op.create_index("ix_video_saves_video_created_at", "video_saves", ["video_id", "created_at"])
    op.create_index("ix_video_saves_user_created_at", "video_saves", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_video_saves_user_created_at", table_name="video_saves")
    op.drop_index("ix_video_saves_video_created_at", table_name="video_saves")
    op.drop_table("video_saves")
    op.drop_index("ix_video_reactions_user_created_at", table_name="video_reactions")
    op.drop_index("ix_video_reactions_video_created_at", table_name="video_reactions")
    op.drop_table("video_reactions")
    op.drop_constraint("ck_videos_like_count_nonnegative", "videos", type_="check")
    op.drop_column("videos", "like_count")
