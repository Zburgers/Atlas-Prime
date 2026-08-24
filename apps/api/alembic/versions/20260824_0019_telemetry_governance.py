"""add playback session and event identity

Revision ID: 20260824_0019
Revises: 20260824_0018
"""

import uuid

import sqlalchemy as sa
from alembic import op


revision = "20260824_0019"
down_revision = "20260824_0018"
branch_labels = None
depends_on = None


def _backfill_identity(bind: sa.Connection) -> None:
    playback_events = sa.table(
        "playback_events",
        sa.column("id", sa.Uuid()),
        sa.column("playback_session_id", sa.Uuid()),
        sa.column("event_id", sa.Uuid()),
    )
    rows = bind.execute(
        sa.select(playback_events.c.id).where(
            sa.or_(playback_events.c.playback_session_id.is_(None), playback_events.c.event_id.is_(None))
        )
    ).scalars()
    for row_id in rows:
        stable_id = uuid.UUID(str(row_id))
        bind.execute(
            sa.update(playback_events)
            .where(playback_events.c.id == row_id)
            .values(
                playback_session_id=uuid.uuid5(uuid.NAMESPACE_URL, f"atlas-prime/playback-session/{stable_id}"),
                event_id=uuid.uuid5(uuid.NAMESPACE_URL, f"atlas-prime/playback-event/{stable_id}"),
            )
        )


def upgrade() -> None:
    op.add_column("playback_events", sa.Column("playback_session_id", sa.Uuid(), nullable=True))
    op.add_column("playback_events", sa.Column("event_id", sa.Uuid(), nullable=True))
    _backfill_identity(op.get_bind())

    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("playback_events", recreate="always") as batch_op:
            batch_op.alter_column("playback_session_id", nullable=False)
            batch_op.alter_column("event_id", nullable=False)
            batch_op.create_unique_constraint("uq_playback_events_event_id", ["event_id"])
    else:
        op.alter_column("playback_events", "playback_session_id", nullable=False)
        op.alter_column("playback_events", "event_id", nullable=False)
        op.create_unique_constraint("uq_playback_events_event_id", "playback_events", ["event_id"])


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("playback_events", recreate="always") as batch_op:
            batch_op.drop_constraint("uq_playback_events_event_id", type_="unique")
            batch_op.drop_column("event_id")
            batch_op.drop_column("playback_session_id")
    else:
        op.drop_constraint("uq_playback_events_event_id", "playback_events", type_="unique")
        op.drop_column("playback_events", "event_id")
        op.drop_column("playback_events", "playback_session_id")
