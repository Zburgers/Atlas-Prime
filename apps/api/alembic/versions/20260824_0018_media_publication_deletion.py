"""persist media publication inventory and deletion state

Revision ID: 20260824_0018
Revises: 20260805_0017
"""

from alembic import op
import sqlalchemy as sa


revision = "20260824_0018"
down_revision = "20260805_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("videos", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "videos",
        sa.Column("deletion_status", sa.Text(), nullable=True, server_default="complete"),
    )
    op.add_column("videos", sa.Column("deletion_error", sa.Text(), nullable=True))

    # Backfill before making the new state required for every existing video.
    op.execute(sa.text("UPDATE videos SET deletion_status = 'complete' WHERE deletion_status IS NULL"))
    op.alter_column("videos", "deletion_status", nullable=False, server_default="complete")
    op.create_check_constraint(
        "ck_videos_deletion_status",
        "videos",
        "deletion_status in ('pending', 'running', 'failed', 'complete')",
    )

    op.create_table(
        "video_asset_inventory",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("video_id", sa.Uuid(), nullable=False),
        sa.Column("generation", sa.Uuid(), nullable=False),
        sa.Column("relative_path", sa.Text(), nullable=False),
        sa.Column("content_type", sa.Text(), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("size_bytes >= 0", name="ck_video_asset_inventory_size_nonnegative"),
        sa.ForeignKeyConstraint(
            ["video_id"],
            ["videos.id"],
            name="fk_video_asset_inventory_video_id_videos",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_video_asset_inventory"),
        sa.UniqueConstraint(
            "video_id",
            "generation",
            "relative_path",
            name="uq_video_asset_inventory_video_generation_path",
        ),
    )
    op.create_index(
        "ix_video_asset_inventory_video_generation",
        "video_asset_inventory",
        ["video_id", "generation"],
    )
    op.create_index("ix_video_asset_inventory_video_id", "video_asset_inventory", ["video_id"])


def downgrade() -> None:
    op.drop_index("ix_video_asset_inventory_video_id", table_name="video_asset_inventory")
    op.drop_index("ix_video_asset_inventory_video_generation", table_name="video_asset_inventory")
    op.drop_table("video_asset_inventory")
    op.drop_constraint("ck_videos_deletion_status", "videos", type_="check")
    op.drop_column("videos", "deletion_error")
    op.drop_column("videos", "deletion_status")
    op.drop_column("videos", "deleted_at")
