from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone

import pytest

from app.worker import analytics
from app.services.telemetry_retention import RetentionSummary


def test_analytics_worker_uses_dedicated_queue_and_daily_schedule() -> None:
    assert analytics.celery_app.conf.task_default_queue == "analytics"
    assert analytics.celery_app.conf.task_routes[analytics.ANALYTICS_REBUILD_TASK]["queue"] == "analytics"
    assert analytics.celery_app.conf.task_routes[analytics.TELEMETRY_PURGE_TASK]["queue"] == "analytics"
    assert analytics.celery_app.conf.beat_schedule["rebuild-recent-daily-analytics"]["task"] == analytics.ANALYTICS_REBUILD_TASK
    assert analytics.celery_app.conf.beat_schedule["purge-raw-playback-telemetry"]["task"] == analytics.TELEMETRY_PURGE_TASK
    assert analytics.celery_app.conf.beat_schedule["purge-raw-playback-telemetry"]["schedule"].hour == {0}
    assert analytics.celery_app.conf.beat_schedule["purge-raw-playback-telemetry"]["schedule"].minute == {20}


def test_analytics_worker_rejects_an_empty_rebuild_window() -> None:
    with pytest.raises(ValueError, match="at least 1"):
        asyncio.run(analytics._rebuild_recent_daily_metrics(0))


def test_analytics_worker_rebuilds_today_and_yesterday(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class FakeSession:
        async def __aenter__(self) -> object:
            return object()

        async def __aexit__(self, *_args: object) -> None:
            return None

    class Result:
        date_from = date(2026, 7, 14)
        date_to = date(2026, 7, 15)
        video_metric_rows = 3
        creator_metric_rows = 2

    async def fake_rebuild(_session: object, *, date_from: date, date_to: date) -> Result:
        captured.update(date_from=date_from, date_to=date_to)
        return Result()

    monkeypatch.setattr(analytics, "SessionLocal", FakeSession)
    monkeypatch.setattr(analytics, "rebuild_daily_metrics", fake_rebuild)
    monkeypatch.setattr(analytics, "date", type("FixedDate", (), {"today": staticmethod(lambda: date(2026, 7, 15))}))

    summary = asyncio.run(analytics._rebuild_recent_daily_metrics(2))

    assert captured == {"date_from": date(2026, 7, 14), "date_to": date(2026, 7, 15)}
    assert summary == {"date_from": "2026-07-14", "date_to": "2026-07-15", "video_metric_rows": 3, "creator_metric_rows": 2}


def test_analytics_worker_purges_telemetry_with_aggregate_summary(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class FakeSession:
        async def __aenter__(self) -> object:
            return object()

        async def __aexit__(self, *_args: object) -> None:
            return None

    async def fake_purge(_session: object, *, cutoff: datetime, batch_size: int, apply: bool) -> RetentionSummary:
        captured.update(cutoff=cutoff, batch_size=batch_size, apply=apply)
        return RetentionSummary(
            cutoff=cutoff,
            batch_size=batch_size,
            eligible_rows=8,
            purged_rows=8,
            batches=3,
            apply=True,
        )

    now = datetime(2026, 7, 15, 0, 20, tzinfo=timezone.utc)
    monkeypatch.setattr(analytics, "SessionLocal", FakeSession)
    monkeypatch.setattr(analytics, "purge_playback_events", fake_purge)

    summary = asyncio.run(analytics._purge_raw_playback_events(batch_size=3, now=now))

    assert captured == {
        "cutoff": datetime(2026, 6, 15, 0, 20, tzinfo=timezone.utc),
        "batch_size": 3,
        "apply": True,
    }
    assert summary == {
        "status": "applied",
        "cutoff": "2026-06-15T00:20:00+00:00",
        "batch_size": 3,
        "eligible_rows": 8,
        "purged_rows": 8,
        "batches": 3,
    }
