from collections.abc import AsyncGenerator, Iterator
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.deps import get_session
from app.db.base import Base
from app.db.models import Video, VideoImpression, VideoView
from app.main import app


@pytest.fixture()
def client() -> Iterator[TestClient]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async def override_session() -> AsyncGenerator[AsyncSession, None]:
        async with session_maker() as session:
            yield session

    async def create_schema() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_schema() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()

    import asyncio

    asyncio.run(create_schema())
    app.dependency_overrides[get_session] = override_session
    app.state.test_session_maker = session_maker
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        del app.state.test_session_maker
        asyncio.run(drop_schema())


@pytest.fixture(autouse=True)
def enable_test_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ATLAS_ALLOW_DEV_AUTH_HEADERS", "true")
    monkeypatch.setenv("ATLAS_ADMIN_CLERK_USER_IDS", "operator")


def _headers(user_id: str) -> dict[str, str]:
    return {
        "X-Atlas-Dev-Clerk-User-Id": user_id,
        "X-Atlas-Dev-Email": f"{user_id}@example.com",
    }


def _utc_datetime(metric_date: date, hour: int) -> datetime:
    return datetime.combine(metric_date, time(hour=hour), tzinfo=timezone.utc)


def _seed_raw_events(client: TestClient, *, video_id: str, metric_date: date) -> None:
    import asyncio

    async def seed() -> None:
        async with app.state.test_session_maker() as session:
            video = await session.get(Video, UUID(video_id))
            assert video is not None
            session.add_all(
                [
                    VideoImpression(video_id=video.id, surface="home", position=0, created_at=_utc_datetime(metric_date, 9)),
                    VideoImpression(video_id=video.id, surface="home", position=1, created_at=_utc_datetime(metric_date, 10)),
                    VideoView(
                        video_id=video.id,
                        session_id=f"{video.id}-session-{metric_date.isoformat()}",
                        position_seconds=Decimal("12.5"),
                        created_at=_utc_datetime(metric_date, 11),
                    ),
                ]
            )
            await session.commit()

    asyncio.run(seed())


def test_daily_metrics_rebuild_is_deterministic_and_studio_scoped_to_creator(client: TestClient) -> None:
    today = date.today()
    yesterday = today - timedelta(days=1)
    owner_video = client.post("/videos", headers=_headers("owner"), json={"title": "Owner lesson"}).json()
    other_video = client.post("/videos", headers=_headers("other"), json={"title": "Other lesson"}).json()
    _seed_raw_events(client, video_id=owner_video["id"], metric_date=yesterday)
    _seed_raw_events(client, video_id=owner_video["id"], metric_date=today)
    _seed_raw_events(client, video_id=other_video["id"], metric_date=today)

    first_rebuild = client.post(
        f"/admin/analytics/rebuild?date_from={yesterday.isoformat()}&date_to={today.isoformat()}",
        headers=_headers("operator"),
    )
    second_rebuild = client.post(
        f"/admin/analytics/rebuild?date_from={yesterday.isoformat()}&date_to={today.isoformat()}",
        headers=_headers("operator"),
    )
    owner_analytics = client.get("/studio/analytics?days=2", headers=_headers("owner"))
    other_analytics = client.get("/studio/analytics?days=2", headers=_headers("other"))

    assert first_rebuild.status_code == 200
    assert first_rebuild.json()["video_metric_rows"] == 3
    assert second_rebuild.status_code == 200
    assert second_rebuild.json() == first_rebuild.json()
    assert owner_analytics.status_code == 200
    owner_body = owner_analytics.json()
    assert owner_body["totals"] == {"impressions": 4, "views": 2, "watch_time_seconds": "25.000"}
    assert [point["date"] for point in owner_body["daily"]] == [yesterday.isoformat(), today.isoformat()]
    assert owner_body["top_videos"] == [
        {
            "video_id": owner_video["id"],
            "title": "Owner lesson",
            "impressions": 4,
            "views": 2,
            "watch_time_seconds": "25.000",
        }
    ]
    assert other_analytics.status_code == 200
    assert other_analytics.json()["top_videos"][0]["video_id"] == other_video["id"]
