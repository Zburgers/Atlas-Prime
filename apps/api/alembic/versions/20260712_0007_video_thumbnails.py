"""add video thumbnails

Revision ID: 20260712_0007
Revises: 20260712_0006
Create Date: 2026-07-12
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260712_0007"
down_revision = "20260712_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "video_thumbnails",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("video_id", sa.Uuid(), nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("content_type", sa.Text(), nullable=False),
        sa.Column("width", sa.BigInteger(), nullable=False),
        sa.Column("height", sa.BigInteger(), nullable=False),
        sa.Column("selected", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("source in ('generated', 'custom')", name="ck_video_thumbnails_source"),
        sa.CheckConstraint("width > 0", name="ck_video_thumbnails_width_positive"),
        sa.CheckConstraint("height > 0", name="ck_video_thumbnails_height_positive"),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("video_id", "storage_key", name="uq_video_thumbnails_video_storage_key"),
    )
    op.create_index("ix_video_thumbnails_video_created_at", "video_thumbnails", ["video_id", "created_at"])
    op.create_index(
        "uq_video_thumbnails_selected_per_video",
        "video_thumbnails",
        ["video_id"],
        unique=True,
        postgresql_where=sa.text("selected"),
        sqlite_where=sa.text("selected"),
    )


def downgrade() -> None:
    op.drop_index("uq_video_thumbnails_selected_per_video", table_name="video_thumbnails")
    op.drop_index("ix_video_thumbnails_video_created_at", table_name="video_thumbnails")
    op.drop_table("video_thumbnails")
