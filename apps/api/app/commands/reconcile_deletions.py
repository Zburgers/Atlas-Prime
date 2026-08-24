from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Video
from app.db.session import SessionLocal
from app.domain.status import DeletionStatus
from app.services.storage import MinioOriginalStorage, MinioProcessedHlsStorage
from app.services.videos import cleanup_deleted_video


@dataclass(frozen=True)
class DeletionCandidate:
    video_id: UUID
    deletion_status: str


async def find_deletion_candidates(session: AsyncSession) -> list[DeletionCandidate]:
    result = await session.execute(
        select(Video.id, Video.deletion_status)
        .where(
            Video.deleted_at.is_not(None),
            Video.active_processing_generation.is_(None),
            Video.deletion_status.in_(
                (
                    DeletionStatus.PENDING.value,
                    DeletionStatus.RUNNING.value,
                    DeletionStatus.FAILED.value,
                )
            ),
        )
        .order_by(Video.updated_at.asc())
    )
    return [DeletionCandidate(video_id=row.id, deletion_status=row.deletion_status) for row in result]


async def run(*, apply: bool) -> list[DeletionCandidate]:
    async with SessionLocal() as session:
        candidates = await find_deletion_candidates(session)

    if not apply:
        print(f"Would reconcile {len(candidates)} tombstoned video(s)")
        for candidate in candidates:
            print(f"  video={candidate.video_id} deletion_status={candidate.deletion_status}")
        return candidates

    original_storage = MinioOriginalStorage()
    processed_storage = MinioProcessedHlsStorage()
    for candidate in candidates:
        await cleanup_deleted_video(
            candidate.video_id,
            original_storage,
            processed_storage,
            session_factory=SessionLocal,
        )
    print(f"Reconciled {len(candidates)} tombstoned video(s)")
    return candidates


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reconcile pending, running, and failed Atlas Prime video tombstones")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="perform idempotent storage cleanup and finalize tombstones; without this flag, list candidates only",
    )
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(run(apply=parse_args().apply))
