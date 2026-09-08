"""add video text tracks

Revision ID: 20260712_0010
Revises: 20260712_0009
Create Date: 2026-07-12
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260712_0010"
down_revision = "20260712_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "video_text_tracks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("video_id", sa.Uuid(), nullable=False),
        sa.Column("language", sa.Text(), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("kind", sa.Text(), server_default="captions", nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("content_type", sa.Text(), server_default="text/vtt", nullable=False),
        sa.Column("is_default", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("kind in ('captions')", name="ck_video_text_tracks_kind"),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("video_id", "language", "kind", name="uq_video_text_tracks_video_language_kind"),
    )
    op.create_index("ix_video_text_tracks_video_created_at", "video_text_tracks", ["video_id", "created_at"])
    op.create_index(
        "uq_video_text_tracks_default_per_video",
        "video_text_tracks",
        ["video_id"],
        unique=True,
        postgresql_where=sa.text("is_default"),
        sqlite_where=sa.text("is_default"),
    )


def downgrade() -> None:
    op.drop_index("uq_video_text_tracks_default_per_video", table_name="video_text_tracks")
    op.drop_index("ix_video_text_tracks_video_created_at", table_name="video_text_tracks")
    op.drop_table("video_text_tracks")
