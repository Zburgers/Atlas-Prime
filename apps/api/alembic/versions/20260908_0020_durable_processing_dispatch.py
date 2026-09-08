"""add durable processing dispatch outbox and impression dedupe

Revision ID: 20260908_0020
Revises: 20260824_0019
"""

import uuid

import sqlalchemy as sa
from alembic import op


revision = "20260908_0020"
down_revision = "20260824_0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "processing_dispatches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.Text(), server_default="pending", nullable=False),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["video_processing_jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id", name="uq_processing_dispatches_job"),
        sa.CheckConstraint("status in ('pending', 'published', 'canceled')", name="ck_processing_dispatches_status"),
    )
    op.create_index("ix_processing_dispatches_status_created_at", "processing_dispatches", ["status", "created_at"])

    bind = op.get_bind()
    jobs = sa.table(
        "video_processing_jobs",
        sa.column("id", sa.Uuid()),
        sa.column("status", sa.Text()),
    )
    dispatches = sa.table(
        "processing_dispatches",
        sa.column("id", sa.Uuid()),
        sa.column("job_id", sa.Uuid()),
        sa.column("status", sa.Text()),
    )
    for job_id in bind.execute(sa.select(jobs.c.id).where(jobs.c.status == "queued")).scalars():
        bind.execute(sa.insert(dispatches).values(id=uuid.uuid4(), job_id=job_id, status="pending"))

    op.add_column("video_impressions", sa.Column("dedupe_key", sa.Text(), nullable=True))
    impressions = sa.table("video_impressions", sa.column("id", sa.Uuid()), sa.column("dedupe_key", sa.Text()))
    for impression_id in bind.execute(sa.select(impressions.c.id).where(impressions.c.dedupe_key.is_(None))).scalars():
        bind.execute(
            sa.update(impressions)
            .where(impressions.c.id == impression_id)
            .values(dedupe_key=str(impression_id))
        )
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("video_impressions", recreate="always") as batch_op:
            batch_op.alter_column("dedupe_key", nullable=False)
            batch_op.create_unique_constraint("uq_video_impressions_dedupe_key", ["dedupe_key"])
    else:
        op.alter_column("video_impressions", "dedupe_key", nullable=False)
        op.create_unique_constraint("uq_video_impressions_dedupe_key", "video_impressions", ["dedupe_key"])


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("video_impressions", recreate="always") as batch_op:
            batch_op.drop_constraint("uq_video_impressions_dedupe_key", type_="unique")
            batch_op.drop_column("dedupe_key")
    else:
        op.drop_constraint("uq_video_impressions_dedupe_key", "video_impressions", type_="unique")
        op.drop_column("video_impressions", "dedupe_key")
    op.drop_index("ix_processing_dispatches_status_created_at", table_name="processing_dispatches")
    op.drop_table("processing_dispatches")
