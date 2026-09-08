"""add channel subscriptions and watch history

Revision ID: 20260712_0011
Revises: 20260712_0010
"""
import sqlalchemy as sa
from alembic import op

revision = "20260712_0011"
down_revision = "20260712_0010"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table("channel_subscriptions", sa.Column("id", sa.Uuid(), nullable=False), sa.Column("user_id", sa.Uuid(), nullable=False), sa.Column("channel_id", sa.Uuid(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.ForeignKeyConstraint(["channel_id"], ["channels.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("user_id", "channel_id", name="uq_channel_subscriptions_user_channel"))
    op.create_index("ix_channel_subscriptions_user_created_at", "channel_subscriptions", ["user_id", "created_at"])
    op.create_table("watch_history", sa.Column("id", sa.Uuid(), nullable=False), sa.Column("user_id", sa.Uuid(), nullable=False), sa.Column("video_id", sa.Uuid(), nullable=False), sa.Column("position_seconds", sa.Numeric(10, 3)), sa.Column("watched_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("user_id", "video_id", name="uq_watch_history_user_video"))
    op.create_index("ix_watch_history_user_watched_at", "watch_history", ["user_id", "watched_at"])

def downgrade() -> None:
    op.drop_table("watch_history"); op.drop_table("channel_subscriptions")
