from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import PlaybackEvent

RETENTION_DAYS = 30
DEFAULT_BATCH_SIZE = 1000
MAX_BATCH_SIZE = 10_000


@dataclass(frozen=True)
class RetentionSummary:
    cutoff: datetime
    batch_size: int
    eligible_rows: int
    purged_rows: int
    batches: int
    apply: bool


def retention_cutoff(*, now: datetime) -> datetime:
    return now.astimezone(timezone.utc) - timedelta(days=RETENTION_DAYS)


def validate_batch_size(batch_size: int) -> int:
    if not 1 <= batch_size <= MAX_BATCH_SIZE:
        raise ValueError(f"batch_size must be between 1 and {MAX_BATCH_SIZE}")
    return batch_size


async def eligible_playback_event_count(session: AsyncSession, *, cutoff: datetime) -> int:
    result = await session.scalar(select(func.count()).select_from(PlaybackEvent).where(PlaybackEvent.created_at < cutoff))
    return int(result or 0)


async def purge_playback_events(
    session: AsyncSession,
    *,
    cutoff: datetime,
    batch_size: int = DEFAULT_BATCH_SIZE,
    apply: bool,
) -> RetentionSummary:
    validate_batch_size(batch_size)
    eligible_rows = await eligible_playback_event_count(session, cutoff=cutoff)
    if not apply:
        return RetentionSummary(
            cutoff=cutoff,
            batch_size=batch_size,
            eligible_rows=eligible_rows,
            purged_rows=0,
            batches=0,
            apply=False,
        )

    purged_rows = 0
    batches = 0
    try:
        while True:
            result = await session.execute(
                select(PlaybackEvent.id)
                .where(PlaybackEvent.created_at < cutoff)
                .order_by(PlaybackEvent.created_at.asc(), PlaybackEvent.id.asc())
                .limit(batch_size)
            )
            event_ids = result.scalars().all()
            if not event_ids:
                break

            delete_result = await session.execute(
                delete(PlaybackEvent).where(
                    PlaybackEvent.id.in_(event_ids),
                    PlaybackEvent.created_at < cutoff,
                )
            )
            await session.commit()
            purged_rows += int(delete_result.rowcount or 0)
            batches += 1
    except Exception:
        await session.rollback()
        raise

    return RetentionSummary(
        cutoff=cutoff,
        batch_size=batch_size,
        eligible_rows=eligible_rows,
        purged_rows=purged_rows,
        batches=batches,
        apply=True,
    )
