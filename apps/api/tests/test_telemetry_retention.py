from __future__ import annotations

import asyncio
import json
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.commands import purge_telemetry
from app.db.base import Base
from app.db.models import PlaybackEvent
from app.services.telemetry_retention import (
    MAX_BATCH_SIZE,
    RetentionSummary,
    purge_playback_events,
    retention_cutoff,
    validate_batch_size,
)


@pytest.fixture()
def session_maker() -> Iterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    maker = async_sessionmaker(engine, expire_on_commit=False)

    async def create_schema() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def drop_schema() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
        await engine.dispose()

    asyncio.run(create_schema())
    try:
        yield maker
    finally:
        asyncio.run(drop_schema())


def _event(*, created_at: datetime) -> PlaybackEvent:
    return PlaybackEvent(
        video_id=uuid4(),
        playback_session_id=uuid4(),
        event_id=uuid4(),
        event_type="play",
        created_at=created_at,
    )


async def _count_events(session: AsyncSession) -> int:
    return int(await session.scalar(select(func.count()).select_from(PlaybackEvent)) or 0)


def test_exact_cutoff_is_retained_and_dry_run_does_not_delete(session_maker: async_sessionmaker[AsyncSession]) -> None:
    now = datetime(2026, 8, 24, 12, 0, tzinfo=timezone.utc)
    cutoff = retention_cutoff(now=now)

    async def scenario() -> None:
        async with session_maker() as session:
            session.add_all(
                [
                    _event(created_at=cutoff - timedelta(microseconds=1)),
                    _event(created_at=cutoff),
                    _event(created_at=cutoff + timedelta(microseconds=1)),
                ]
            )
            await session.commit()
            summary = await purge_playback_events(session, cutoff=cutoff, batch_size=2, apply=False)
            assert summary == RetentionSummary(cutoff, 2, 1, 0, 0, False)
            assert await _count_events(session) == 3

    asyncio.run(scenario())


def test_apply_deletes_in_small_batches_and_rerun_is_idempotent(session_maker: async_sessionmaker[AsyncSession]) -> None:
    now = datetime(2026, 8, 24, 12, 0, tzinfo=timezone.utc)
    cutoff = retention_cutoff(now=now)

    async def scenario() -> None:
        async with session_maker() as session:
            session.add_all([_event(created_at=cutoff - timedelta(days=index + 1)) for index in range(5)])
            await session.commit()
            summary = await purge_playback_events(session, cutoff=cutoff, batch_size=2, apply=True)
            assert summary == RetentionSummary(cutoff, 2, 5, 5, 3, True)
            assert await _count_events(session) == 0

            rerun = await purge_playback_events(session, cutoff=cutoff, batch_size=2, apply=True)
            assert rerun == RetentionSummary(cutoff, 2, 0, 0, 0, True)

    asyncio.run(scenario())


def test_batch_size_validation() -> None:
    assert validate_batch_size(1) == 1
    assert validate_batch_size(MAX_BATCH_SIZE) == MAX_BATCH_SIZE
    with pytest.raises(ValueError, match="between 1"):
        validate_batch_size(0)
    with pytest.raises(ValueError, match="between 1"):
        validate_batch_size(MAX_BATCH_SIZE + 1)


def test_command_defaults_to_sanitized_dry_run(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    captured: dict[str, object] = {}
    fixed_now = datetime(2026, 8, 24, 12, 0, tzinfo=timezone.utc)

    class FakeSession:
        async def __aenter__(self) -> object:
            return object()

        async def __aexit__(self, *_args: object) -> None:
            return None

    async def fake_purge(_session: object, *, cutoff: datetime, batch_size: int, apply: bool) -> RetentionSummary:
        captured.update(cutoff=cutoff, batch_size=batch_size, apply=apply)
        return RetentionSummary(cutoff, batch_size, 4, 0, 0, False)

    monkeypatch.setattr(purge_telemetry, "SessionLocal", FakeSession)
    monkeypatch.setattr(purge_telemetry, "purge_playback_events", fake_purge)

    asyncio.run(purge_telemetry.run(apply=False, batch_size=7, now=fixed_now))
    output = json.loads(capsys.readouterr().out)

    assert captured == {"cutoff": retention_cutoff(now=fixed_now), "batch_size": 7, "apply": False}
    assert output == {
        "status": "dry_run",
        "cutoff": "2026-07-25T12:00:00+00:00",
        "batch_size": 7,
        "eligible_rows": 4,
        "purged_rows": 0,
        "batches": 0,
    }
    assert "video_id" not in json.dumps(output)
