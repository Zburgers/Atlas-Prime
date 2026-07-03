"""add channels

Revision ID: 20260702_0002
Revises: 20260628_0001
Create Date: 2026-07-02
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260702_0002"
down_revision = "20260628_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "channels",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("handle", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("avatar_storage_key", sa.Text(), nullable=True),
        sa.Column("banner_storage_key", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("length(handle) >= 3", name="ck_channels_handle_min_length"),
        sa.CheckConstraint("length(display_name) >= 1", name="ck_channels_display_name_min_length"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_user_id", name="uq_channels_owner_user_id"),
        sa.UniqueConstraint("handle", name="uq_channels_handle"),
    )
    op.create_index("ix_channels_handle", "channels", ["handle"])
    op.add_column("videos", sa.Column("channel_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_videos_channel_id_channels",
        "videos",
        "channels",
        ["channel_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_videos_channel_created_at", "videos", ["channel_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_videos_channel_created_at", table_name="videos")
    op.drop_constraint("fk_videos_channel_id_channels", "videos", type_="foreignkey")
    op.drop_column("videos", "channel_id")
    op.drop_index("ix_channels_handle", table_name="channels")
    op.drop_table("channels")
