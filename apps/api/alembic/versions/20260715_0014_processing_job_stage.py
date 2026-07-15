"""add processing job stage

Revision ID: 20260715_0014
Revises: 20260715_0013
"""

import sqlalchemy as sa
from alembic import op

revision = "20260715_0014"
down_revision = "20260715_0013"
branch_labels = None
depends_on = None

STAGE_VALUES = "'queued', 'downloading', 'probing', 'packaging', 'uploading', 'complete', 'failed'"


def upgrade() -> None:
    op.add_column("video_processing_jobs", sa.Column("stage", sa.Text(), nullable=False, server_default="queued"))
    op.create_check_constraint("ck_video_processing_jobs_stage", "video_processing_jobs", f"stage in ({STAGE_VALUES})")


def downgrade() -> None:
    op.drop_constraint("ck_video_processing_jobs_stage", "video_processing_jobs", type_="check")
    op.drop_column("video_processing_jobs", "stage")
