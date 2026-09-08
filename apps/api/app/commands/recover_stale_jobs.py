from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import config
from app.db.models import Video, VideoProcessingJob
from app.db.session import SessionLocal
from app.domain.status import JobStatus, ProcessingStage, VideoStatus


@dataclass(frozen=True)
class StaleJob:
    job_id: UUID
    video_id: UUID
    generation: UUID
    started_at: datetime
    video_status: str


class _RecoveryFenceLost(Exception):
    """A candidate changed before both recovery updates could be applied."""


def stale_cutoff(*, now: datetime, stale_seconds: int) -> datetime:
    return now - timedelta(seconds=max(60, stale_seconds))


def is_stale_started_at(*, started_at: datetime | None, cutoff: datetime) -> bool:
    return started_at is not None and started_at < cutoff


def generation_is_current(*, job_generation: UUID, active_generation: UUID | None) -> bool:
    return active_generation == job_generation


def stale_jobs_query(*, cutoff: datetime):
    return (
        select(
            VideoProcessingJob.id,
            VideoProcessingJob.video_id,
            VideoProcessingJob.generation,
            VideoProcessingJob.started_at,
            Video.status.label("video_status"),
        )
        .join(Video, Video.id == VideoProcessingJob.video_id)
        .where(
            VideoProcessingJob.status == JobStatus.RUNNING.value,
            VideoProcessingJob.started_at.is_not(None),
            VideoProcessingJob.started_at < cutoff,
        )
        .order_by(VideoProcessingJob.started_at.asc())
    )


async def find_stale_jobs(session: AsyncSession, *, cutoff: datetime) -> list[StaleJob]:
    result = await session.execute(stale_jobs_query(cutoff=cutoff))
    return [
        StaleJob(
            job_id=row.id,
            video_id=row.video_id,
            generation=row.generation,
            started_at=row.started_at,
            video_status=row.video_status,
        )
        for row in result
    ]


async def recover_stale_jobs(session: AsyncSession, *, cutoff: datetime, apply: bool) -> list[StaleJob]:
    """List stale jobs, or fail only still-active matching generations.

    No retry is enqueued here. A superseded generation fails the conditional
    UPDATE and is reported as no longer recoverable.
    """
    stale = await find_stale_jobs(session, cutoff=cutoff)
    if not apply:
        return stale

    recovered: list[StaleJob] = []
    for candidate in stale:
        try:
            async with session.begin_nested():
                job_result = await session.execute(
                    update(VideoProcessingJob)
                    .where(
                        VideoProcessingJob.id == candidate.job_id,
                        VideoProcessingJob.video_id == candidate.video_id,
                        VideoProcessingJob.generation == candidate.generation,
                        VideoProcessingJob.status == JobStatus.RUNNING.value,
                        VideoProcessingJob.started_at == candidate.started_at,
                        VideoProcessingJob.video.has(
                            and_(
                                Video.id == candidate.video_id,
                                Video.active_processing_generation == candidate.generation,
                                Video.status == candidate.video_status,
                                Video.status.in_(
                                    (
                                        VideoStatus.QUEUED.value,
                                        VideoStatus.PROBING.value,
                                        VideoStatus.PROCESSING.value,
                                    )
                                ),
                            )
                        ),
                    )
                    .values(
                        status=JobStatus.FAILED.value,
                        stage=ProcessingStage.FAILED.value,
                        finished_at=datetime.now(timezone.utc),
                        error_code="STALE_PROCESSING_JOB",
                        error_message="Processing job exceeded the stale recovery threshold",
                    )
                )
                if job_result.rowcount != 1:
                    raise _RecoveryFenceLost

                video_result = await session.execute(
                    update(Video)
                    .where(
                        Video.id == candidate.video_id,
                        Video.active_processing_generation == candidate.generation,
                        Video.status == candidate.video_status,
                        Video.status.in_(
                            (
                                VideoStatus.QUEUED.value,
                                VideoStatus.PROBING.value,
                                VideoStatus.PROCESSING.value,
                            )
                        ),
                    )
                    .values(
                        status=VideoStatus.FAILED.value,
                        failure_code="STALE_PROCESSING_JOB",
                        failure_message="Processing job exceeded the stale recovery threshold",
                    )
                )
                if video_result.rowcount != 1:
                    raise _RecoveryFenceLost
        except _RecoveryFenceLost:
            continue
        recovered.append(candidate)
    await session.commit()
    return recovered


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect or fail abandoned Atlas Prime processing jobs (dry-run by default)"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="fail matching stale jobs; without this flag, perform a dry run",
    )
    parser.add_argument(
        "--stale-seconds",
        type=int,
        default=None,
        help="override ATLAS_PROCESSING_STALE_SECONDS (default 900; minimum 60)",
    )
    return parser.parse_args()


async def run(*, apply: bool, stale_seconds: int | None = None) -> list[StaleJob]:
    threshold = config.processing_stale_seconds() if stale_seconds is None else max(60, stale_seconds)
    cutoff = stale_cutoff(now=datetime.now(timezone.utc), stale_seconds=threshold)
    async with SessionLocal() as session:
        jobs = await recover_stale_jobs(session, cutoff=cutoff, apply=apply)
    action = "Recovered" if apply else "Would recover"
    print(f"{action} {len(jobs)} stale processing job(s) older than {threshold}s")
    for job in jobs:
        print(f"  job={job.job_id} video={job.video_id} generation={job.generation}")
    return jobs


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(run(apply=args.apply, stale_seconds=args.stale_seconds))
