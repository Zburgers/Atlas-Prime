"""add processing generation identity and active-job uniqueness

Revision ID: 20260805_0017
Revises: 20260715_0016
"""

from alembic import op
import sqlalchemy as sa


revision = "20260805_0017"
down_revision = "20260715_0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("videos", sa.Column("active_processing_generation", sa.Uuid(), nullable=True))
    op.add_column("video_processing_jobs", sa.Column("generation", sa.Uuid(), nullable=True))

    # UUIDs derived from immutable job IDs make the backfill repeatable without
    # relying on random database state or an application-side migration script.
    op.execute(
        sa.text(
            "UPDATE video_processing_jobs "
            "SET generation = md5(id::text)::uuid "
            "WHERE generation IS NULL"
        )
    )

    # Preserve the newest active job deterministically and make older active
    # rows terminal before the partial unique index is installed.
    op.execute(
        sa.text(
            "WITH ranked AS ("
            " SELECT id, row_number() OVER ("
            "   PARTITION BY video_id ORDER BY created_at DESC, id DESC"
            " ) AS position"
            " FROM video_processing_jobs"
            " WHERE status IN ('queued', 'running')"
            ")"
            " UPDATE video_processing_jobs AS job"
            " SET status = 'failed', stage = 'failed',"
            "     error_code = 'superseded_generation_backfill',"
            "     error_message = 'Superseded by the newest active processing generation'"
            " FROM ranked"
            " WHERE job.id = ranked.id AND ranked.position > 1"
        )
    )
    op.execute(
        sa.text(
            "UPDATE videos AS video SET active_processing_generation = active.generation "
            "FROM ("
            " SELECT DISTINCT ON (video_id) video_id, generation"
            " FROM video_processing_jobs"
            " WHERE status IN ('queued', 'running')"
            " ORDER BY video_id, created_at DESC, id DESC"
            ") AS active"
            " WHERE video.id = active.video_id"
        )
    )
    op.alter_column("video_processing_jobs", "generation", nullable=False)
    op.create_index(
        "uq_video_processing_jobs_active_video",
        "video_processing_jobs",
        ["video_id"],
        unique=True,
        postgresql_where=sa.text("status in ('queued', 'running')"),
    )


def downgrade() -> None:
    op.drop_index("uq_video_processing_jobs_active_video", table_name="video_processing_jobs")
    op.drop_column("video_processing_jobs", "generation")
    op.drop_column("videos", "active_processing_generation")
