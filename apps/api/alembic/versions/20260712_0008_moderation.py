"""add moderation reports and audit trail

Revision ID: 20260712_0008
Revises: 20260712_0007
Create Date: 2026-07-12
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260712_0008"
down_revision = "20260712_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("videos", sa.Column("moderation_status", sa.Text(), server_default="approved", nullable=False))
    op.create_check_constraint(
        "ck_videos_moderation_status",
        "videos",
        "moderation_status in ('pending', 'approved', 'limited', 'removed', 'rejected')",
    )
    op.add_column("video_comments", sa.Column("moderation_status", sa.Text(), server_default="approved", nullable=False))
    op.create_check_constraint(
        "ck_video_comments_moderation_status",
        "video_comments",
        "moderation_status in ('pending', 'approved', 'limited', 'removed', 'rejected')",
    )
    op.create_table(
        "content_reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("reporter_user_id", sa.Uuid(), nullable=True),
        sa.Column("target_type", sa.Text(), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), server_default="open", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("target_type in ('video', 'comment')", name="ck_content_reports_target_type"),
        sa.CheckConstraint("status in ('open', 'actioned', 'dismissed')", name="ck_content_reports_status"),
        sa.ForeignKeyConstraint(["reporter_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_content_reports_status_created_at", "content_reports", ["status", "created_at"])
    op.create_index("ix_content_reports_target", "content_reports", ["target_type", "target_id"])
    op.create_table(
        "moderation_actions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("target_type", sa.Text(), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("target_type in ('video', 'comment')", name="ck_moderation_actions_target_type"),
        sa.CheckConstraint("action in ('remove', 'restore', 'limit')", name="ck_moderation_actions_action"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_moderation_actions_target_created_at", "moderation_actions", ["target_type", "target_id", "created_at"])
    op.create_table(
        "audit_log_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("target_type", sa.Text(), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_log_entries_target_created_at", "audit_log_entries", ["target_type", "target_id", "created_at"])
    op.create_index("ix_audit_log_entries_actor_created_at", "audit_log_entries", ["actor_user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_audit_log_entries_actor_created_at", table_name="audit_log_entries")
    op.drop_index("ix_audit_log_entries_target_created_at", table_name="audit_log_entries")
    op.drop_table("audit_log_entries")
    op.drop_index("ix_moderation_actions_target_created_at", table_name="moderation_actions")
    op.drop_table("moderation_actions")
    op.drop_index("ix_content_reports_target", table_name="content_reports")
    op.drop_index("ix_content_reports_status_created_at", table_name="content_reports")
    op.drop_table("content_reports")
    op.drop_constraint("ck_video_comments_moderation_status", "video_comments", type_="check")
    op.drop_column("video_comments", "moderation_status")
    op.drop_constraint("ck_videos_moderation_status", "videos", type_="check")
    op.drop_column("videos", "moderation_status")
