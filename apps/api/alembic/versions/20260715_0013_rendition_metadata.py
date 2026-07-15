"""add rendition output metadata

Revision ID: 20260715_0013
Revises: 20260715_0012
"""

import sqlalchemy as sa
from alembic import op

revision = "20260715_0013"
down_revision = "20260715_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("video_renditions", sa.Column("video_codec", sa.Text(), nullable=True))
    op.add_column("video_renditions", sa.Column("segment_count", sa.Integer(), nullable=True))
    op.add_column("video_renditions", sa.Column("output_size_bytes", sa.BigInteger(), nullable=True))


def downgrade() -> None:
    op.drop_column("video_renditions", "output_size_bytes")
    op.drop_column("video_renditions", "segment_count")
    op.drop_column("video_renditions", "video_codec")
