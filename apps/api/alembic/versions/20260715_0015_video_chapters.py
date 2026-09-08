"""add video chapters

Revision ID: 20260715_0015
Revises: 20260715_0014
"""

import sqlalchemy as sa
from alembic import op

revision = "20260715_0015"
down_revision = "20260715_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "video_chapters",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("video_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("start_seconds", sa.Numeric(10, 3), nullable=False),
        sa.CheckConstraint("position >= 0", name="ck_video_chapters_position_nonnegative"),
        sa.CheckConstraint("start_seconds >= 0", name="ck_video_chapters_start_nonnegative"),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("video_id", "position", name="uq_video_chapters_video_position"),
        sa.UniqueConstraint("video_id", "start_seconds", name="uq_video_chapters_video_start"),
    )
    op.create_index("ix_video_chapters_video_position", "video_chapters", ["video_id", "position"])


def downgrade() -> None:
    op.drop_table("video_chapters")
