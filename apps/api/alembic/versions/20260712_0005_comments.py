"""add video comments

Revision ID: 20260712_0005
Revises: 20260703_0004
Create Date: 2026-07-12
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260712_0005"
down_revision = "20260703_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "video_comments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("video_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("length(body) >= 1", name="ck_video_comments_body_min_length"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_video_comments_video_created_at", "video_comments", ["video_id", "created_at"])
    op.create_index("ix_video_comments_user_created_at", "video_comments", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_video_comments_user_created_at", table_name="video_comments")
    op.drop_index("ix_video_comments_video_created_at", table_name="video_comments")
    op.drop_table("video_comments")
