from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql

from app.commands.recover_stale_jobs import (
    StaleJob,
    generation_is_current,
    is_stale_started_at,
    recover_stale_jobs,
    stale_cutoff,
    stale_jobs_query,
)
from app.core import config


class _Result:
    def __init__(self, rows: list[object] | None = None, rowcount: int | None = None) -> None:
        self._rows = rows or []
        self.rowcount = rowcount

    def __iter__(self):
        return iter(self._rows)


class _NestedTransaction:
    def __init__(self, session: "_Session") -> None:
        self.session = session
        self.snapshot: tuple[str, str, str | None] | None = None

    async def __aenter__(self):
        self.snapshot = self.session._snapshot()
        return self

    async def __aexit__(self, exc_type, _exc, _traceback):
        if exc_type is not None:
            assert self.snapshot is not None
            self.session._restore(self.snapshot)
            self.session.rollbacks += 1
        return False


class _Session:
    def __init__(
        self,
        rows: list[object],
        update_rowcounts: list[int],
        *,
        job_status: str = "running",
        video_status: str = "processing",
        video_failure_code: str | None = None,
    ) -> None:
        self.rows = rows
        self.update_rowcounts = update_rowcounts
        self.statements: list[object] = []
        self.commits = 0
        self.rollbacks = 0
        self.job_status = job_status
        self.video_status = video_status
        self.video_failure_code = video_failure_code
        self.job_update_attempts = 0
        self.video_update_attempts = 0

    async def execute(self, statement):
        self.statements.append(statement)
        if len(self.statements) == 1:
            return _Result(rows=self.rows)
        rowcount = self.update_rowcounts.pop(0)
        if len(self.statements) == 2:
            self.job_update_attempts += 1
            if rowcount == 1:
                self.job_status = "failed"
        else:
            self.video_update_attempts += 1
            if rowcount == 1:
                self.video_status = "failed"
                self.video_failure_code = "STALE_PROCESSING_JOB"
        return _Result(rowcount=rowcount)

    def begin_nested(self):
        return _NestedTransaction(self)

    def _snapshot(self) -> tuple[str, str, str | None]:
        return self.job_status, self.video_status, self.video_failure_code

    def _restore(self, snapshot: tuple[str, str, str | None]) -> None:
        self.job_status, self.video_status, self.video_failure_code = snapshot

    async def commit(self) -> None:
        self.commits += 1


def _stale_job(*, started_at: datetime | None = None, video_status: str = "processing") -> StaleJob:
    return StaleJob(
        job_id=uuid4(),
        video_id=uuid4(),
        generation=uuid4(),
        started_at=started_at or datetime(2026, 8, 24, 10, 0, tzinfo=timezone.utc),
        video_status=video_status,
    )


def _query_row(candidate: StaleJob) -> SimpleNamespace:
    return SimpleNamespace(
        id=candidate.job_id,
        video_id=candidate.video_id,
        generation=candidate.generation,
        started_at=candidate.started_at,
        video_status=candidate.video_status,
    )


def test_stale_threshold_defaults_to_900_and_has_lower_bound(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ATLAS_PROCESSING_STALE_SECONDS", raising=False)
    assert config.processing_stale_seconds() == 900
    monkeypatch.setenv("ATLAS_PROCESSING_STALE_SECONDS", "5")
    assert config.processing_stale_seconds() == 60
    monkeypatch.setenv("ATLAS_PROCESSING_STALE_SECONDS", "not-a-number")
    assert config.processing_stale_seconds() == 900


def test_fresh_job_is_not_recoverable() -> None:
    now = datetime.now(timezone.utc)
    cutoff = stale_cutoff(now=now, stale_seconds=60)
    assert not is_stale_started_at(started_at=now - timedelta(seconds=59), cutoff=cutoff)


def test_stale_job_is_recoverable_candidate() -> None:
    now = datetime.now(timezone.utc)
    cutoff = stale_cutoff(now=now, stale_seconds=60)
    assert is_stale_started_at(started_at=now - timedelta(seconds=61), cutoff=cutoff)


def test_superseded_generation_is_not_current() -> None:
    generation = uuid4()
    assert not generation_is_current(job_generation=generation, active_generation=uuid4())


def test_stale_job_query_is_bounded_to_running_started_jobs() -> None:
    # The query shape is the safety boundary: it never selects queued/succeeded
    # jobs and never treats a missing started_at as stale. Superseded jobs are
    # filtered by the generation predicate in the apply UPDATE.
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=900)
    sql = str(stale_jobs_query(cutoff=cutoff).compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
    assert "status = 'running'" in sql
    assert "started_at IS NOT NULL" in sql
    assert "started_at <" in sql
    assert "JOIN videos" in sql


def test_dry_run_only_selects_candidates_and_does_not_mutate() -> None:
    candidate = _stale_job()
    session = _Session(
        [_query_row(candidate)],
        [],
    )

    result = asyncio.run(
        recover_stale_jobs(
            session,
            cutoff=datetime(2026, 8, 24, 11, 0, tzinfo=timezone.utc),
            apply=False,
        )
    )

    assert result == [candidate]
    assert len(session.statements) == 1
    assert session.commits == 0


def test_apply_fails_job_and_matching_video_generation() -> None:
    candidate = _stale_job()
    session = _Session([_query_row(candidate)], [1, 1])

    result = asyncio.run(
        recover_stale_jobs(
            session,
            cutoff=datetime(2026, 8, 24, 11, 0, tzinfo=timezone.utc),
            apply=True,
        )
    )

    assert result == [candidate]
    assert len(session.statements) == 3
    assert session.commits == 1


def test_video_fence_loss_rolls_back_job_update_without_recovery_or_mutation() -> None:
    candidate = _stale_job()
    session = _Session(
        [_query_row(candidate)],
        [1, 0],
        video_status=candidate.video_status,
    )

    result = asyncio.run(
        recover_stale_jobs(
            session,
            cutoff=datetime(2026, 8, 24, 11, 0, tzinfo=timezone.utc),
            apply=True,
        )
    )

    assert result == []
    assert len(session.statements) == 3
    assert session.commits == 1
    assert session.rollbacks == 1
    assert session.job_update_attempts == 1
    assert session.job_status == "running"
    assert session.video_update_attempts == 1
    assert session.video_status == candidate.video_status
    assert session.video_failure_code is None


def test_superseded_generation_skips_without_video_mutation_or_retry() -> None:
    candidate = _stale_job()
    session = _Session([_query_row(candidate)], [0])

    result = asyncio.run(
        recover_stale_jobs(
            session,
            cutoff=datetime(2026, 8, 24, 11, 0, tzinfo=timezone.utc),
            apply=True,
        )
    )

    assert result == []
    assert len(session.statements) == 2
    assert session.commits == 1


def test_changed_started_at_skips_without_video_mutation() -> None:
    candidate = _stale_job()
    session = _Session([_query_row(candidate)], [0])

    asyncio.run(
        recover_stale_jobs(
            session,
            cutoff=datetime(2026, 8, 24, 11, 0, tzinfo=timezone.utc),
            apply=True,
        )
    )

    job_update_sql = str(
        session.statements[1].compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )
    assert "started_at = '2026-08-24 10:00:00+00:00'" in job_update_sql
