from collections.abc import AsyncGenerator, Iterator
from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.deps import get_session
from app.db.base import Base
from app.db.models import Video, VideoRendition
from app.domain.ranking import HOME_FEED_ALGORITHM_VERSION, home_feed_score
from app.domain.status import RenditionStatus, VideoPrivacy, VideoStatus
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
def enable_dev_auth_headers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ATLAS_ALLOW_DEV_AUTH_HEADERS", "true")


def _headers(user_id: str = "user_123", email: str = "user@example.com") -> dict[str, str]:
    return {
        "X-Atlas-Dev-Clerk-User-Id": user_id,
        "X-Atlas-Dev-Email": email,
    }


def _mark_video_ready(
    client: TestClient,
    *,
    video_id: str,
    privacy: VideoPrivacy = VideoPrivacy.PUBLIC,
    created_at: datetime | None = None,
    views: int = 0,
    likes: int = 0,
) -> None:
    import asyncio

    async def mark_ready() -> None:
        async with app.state.test_session_maker() as session:
            video = await session.get(Video, UUID(video_id))
            assert video is not None
            video.status = VideoStatus.READY.value
            video.privacy = privacy.value
            video.view_count = views
            video.like_count = likes
            video.hls_master_storage_key = f"processed/{video_id}/hls/master.m3u8"
            video.thumbnail_storage_key = f"processed/{video_id}/hls/thumbnail.jpg"
            if created_at is not None:
                video.created_at = created_at
                video.updated_at = created_at
            session.add(
                VideoRendition(
                    video_id=video.id,
                    label="360p",
                    width=640,
                    height=360,
                    target_bitrate=800_000,
                    playlist_storage_key=f"processed/{video_id}/hls/360p/playlist.m3u8",
                    status=RenditionStatus.READY.value,
                )
            )
            await session.commit()

    asyncio.run(mark_ready())


def test_home_feed_ranks_public_ready_videos_by_quality_and_freshness(client: TestClient) -> None:
    now = datetime.now(timezone.utc)
    strong = client.post("/videos", headers=_headers("owner"), json={"title": "Strong older"}).json()
    fresh = client.post("/videos", headers=_headers("owner"), json={"title": "Fresh low signal"}).json()
    private = client.post("/videos", headers=_headers("owner"), json={"title": "Private ready"}).json()
    draft = client.post("/videos", headers=_headers("owner"), json={"title": "Public draft"}).json()
    tombstoned = client.post("/videos", headers=_headers("owner"), json={"title": "Tombstoned public"}).json()
    _mark_video_ready(client, video_id=strong["id"], created_at=now - timedelta(days=5), views=120, likes=14)
    _mark_video_ready(client, video_id=fresh["id"], created_at=now - timedelta(hours=1), views=1, likes=0)
    _mark_video_ready(client, video_id=private["id"], privacy=VideoPrivacy.PRIVATE, views=999, likes=999)
    _mark_video_ready(client, video_id=tombstoned["id"], views=999, likes=999)
    client.patch(f"/videos/{draft['id']}", headers=_headers("owner"), json={"privacy": "public"})

    import asyncio

    async def tombstone() -> None:
        async with app.state.test_session_maker() as session:
            video = await session.get(Video, UUID(tombstoned["id"]))
            assert video is not None
            video.deleted_at = datetime.now(timezone.utc)
            await session.commit()

    asyncio.run(tombstone())

    response = client.get("/feed/home")

    assert response.status_code == 200
    body = response.json()
    assert body["surface"] == "home"
    assert body["algorithm_version"] == HOME_FEED_ALGORITHM_VERSION
    assert body["request_id"].startswith("home-")
    assert body["total"] == 2
    assert [item["video"]["title"] for item in body["items"]] == ["Strong older", "Fresh low signal"]
    assert [item["rank"] for item in body["items"]] == [1, 2]
    assert all(item["reason"] for item in body["items"])
    assert body["items"][0]["score"] > body["items"][1]["score"]


def test_home_feed_request_id_can_be_supplied(client: TestClient) -> None:
    video = client.post("/videos", headers=_headers("owner"), json={"title": "One feed item"}).json()
    _mark_video_ready(client, video_id=video["id"], views=2, likes=1)

    response = client.get("/feed/home?request_id=client-request-1")

    assert response.status_code == 200
    body = response.json()
    assert body["request_id"] == "client-request-1"
    assert body["items"][0]["request_id"] == "client-request-1"
    assert body["items"][0]["surface"] == "home"


def test_home_feed_ranking_function_is_deterministic() -> None:
    created_at = datetime(2026, 7, 1, tzinfo=timezone.utc)
    now = datetime(2026, 7, 12, tzinfo=timezone.utc)

    first = home_feed_score(view_count=12, like_count=3, created_at=created_at, now=now)
    second = home_feed_score(view_count=12, like_count=3, created_at=created_at, now=now)
    weaker = home_feed_score(view_count=1, like_count=0, created_at=created_at, now=now)

    assert first == second
    assert first > weaker


def test_trending_feed_ranks_public_ready_videos_and_replays_request_results(client: TestClient) -> None:
    now = datetime.now(timezone.utc)
    popular = client.post("/videos", headers=_headers("popular-owner"), json={"title": "Popular this week"}).json()
    recent = client.post("/videos", headers=_headers("recent-owner"), json={"title": "Recent discovery"}).json()
    private = client.post("/videos", headers=_headers("private-owner"), json={"title": "Private viral"}).json()
    _mark_video_ready(client, video_id=popular["id"], created_at=now - timedelta(days=2), views=300, likes=20)
    _mark_video_ready(client, video_id=recent["id"], created_at=now - timedelta(hours=1), views=4, likes=0)
    _mark_video_ready(client, video_id=private["id"], privacy=VideoPrivacy.PRIVATE, views=999, likes=999)

    response = client.get("/feed/trending?request_id=trending-request-1", headers=_headers("viewer"))
    replay = client.get("/feed/trending?request_id=trending-request-1", headers=_headers("viewer"))

    assert response.status_code == 200
    assert replay.status_code == 200
    assert replay.json() == response.json()
    body = response.json()
    assert body["surface"] == "trending"
    assert body["algorithm_version"] == "trending-v1"
    assert [item["video"]["title"] for item in body["items"]] == ["Popular this week", "Recent discovery"]
    assert all(item["reason"] == "trending public video" for item in body["items"])


def test_related_videos_prioritize_same_channel_and_exclude_current_and_nonpublic(client: TestClient) -> None:
    current = client.post("/videos", headers=_headers("creator"), json={"title": "Current video"}).json()
    same_channel = client.post("/videos", headers=_headers("creator"), json={"title": "Same channel next"}).json()
    other_channel = client.post("/videos", headers=_headers("other"), json={"title": "Other channel next"}).json()
    unlisted = client.post("/videos", headers=_headers("creator"), json={"title": "Unlisted video"}).json()
    _mark_video_ready(client, video_id=current["id"], views=1)
    _mark_video_ready(client, video_id=same_channel["id"], views=1)
    _mark_video_ready(client, video_id=other_channel["id"], views=200, likes=10)
    _mark_video_ready(client, video_id=unlisted["id"], privacy=VideoPrivacy.UNLISTED, views=999, likes=999)

    response = client.get(f"/videos/{current['id']}/related?request_id=related-request-1", headers=_headers("viewer"))

    assert response.status_code == 200
    body = response.json()
    assert body["surface"] == "related"
    assert body["algorithm_version"] == "related-v1"
    assert [item["video"]["title"] for item in body["items"]] == ["Same channel next", "Other channel next"]
    assert all(item["video"]["id"] != current["id"] for item in body["items"])
    assert all(item["video"]["privacy"] == "public" for item in body["items"])
    assert body["items"][0]["reason"] == "same channel public video"
