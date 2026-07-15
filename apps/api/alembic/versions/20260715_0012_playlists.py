"""add playlists

Revision ID: 20260715_0012
Revises: 20260712_0011
"""
import sqlalchemy as sa
from alembic import op

revision = "20260715_0012"
down_revision = "20260712_0011"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table("playlists", sa.Column("id", sa.Uuid(), nullable=False), sa.Column("owner_id", sa.Uuid(), nullable=False), sa.Column("title", sa.Text(), nullable=False), sa.Column("description", sa.Text()), sa.Column("privacy", sa.Text(), server_default="private", nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.CheckConstraint("privacy in ('private', 'public')", name="ck_playlists_privacy"), sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_playlists_owner_created_at", "playlists", ["owner_id", "created_at"])
    op.create_table("playlist_items", sa.Column("id", sa.Uuid(), nullable=False), sa.Column("playlist_id", sa.Uuid(), nullable=False), sa.Column("video_id", sa.Uuid(), nullable=False), sa.Column("position", sa.Integer(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.ForeignKeyConstraint(["playlist_id"], ["playlists.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("playlist_id", "video_id", name="uq_playlist_items_playlist_video"), sa.UniqueConstraint("playlist_id", "position", name="uq_playlist_items_playlist_position"))
    op.create_index("ix_playlist_items_playlist_position", "playlist_items", ["playlist_id", "position"])

def downgrade() -> None:
    op.drop_table("playlist_items"); op.drop_table("playlists")
