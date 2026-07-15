"""add playback token version

Revision ID: 20260715_0016
Revises: 20260715_0015
"""
import sqlalchemy as sa
from alembic import op

revision = "20260715_0016"
down_revision = "20260715_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("videos", sa.Column("playback_token_version", sa.Integer(), nullable=False, server_default="1"))


def downgrade() -> None:
    op.drop_column("videos", "playback_token_version")
