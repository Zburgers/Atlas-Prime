from collections.abc import AsyncGenerator, Iterator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.deps import get_session
from app.db.base import Base
from app.db.models import Video, VideoRendition
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


def _mark_video_ready(client: TestClient, *, video_id: str, privacy: VideoPrivacy = VideoPrivacy.PUBLIC) -> None:
    import asyncio

    async def mark_ready() -> None:
        async with app.state.test_session_maker() as session:
            video = await session.get(Video, UUID(video_id))
            assert video is not None
            video.status = VideoStatus.READY.value
            video.privacy = privacy.value
            video.hls_master_storage_key = f"processed/{video_id}/hls/master.m3u8"
            video.thumbnail_storage_key = f"processed/{video_id}/hls/thumbnail.jpg"
            video.duration_seconds = 20
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


def test_impression_event_records_surface_position_and_request_id(client: TestClient) -> None:
    video = client.post("/videos", headers=_headers("owner"), json={"title": "Seen card"}).json()
    _mark_video_ready(client, video_id=video["id"], privacy=VideoPrivacy.PUBLIC)

    response = client.post(
        f"/videos/{video['id']}/impressions",
        json={"surface": "home", "position": 2, "request_id": "feed-123"},
    )
    list_response = client.get("/videos")

    assert response.status_code == 201
    body = response.json()
    assert body["video_id"] == video["id"]
    assert body["surface"] == "home"
    assert body["position"] == 2
    assert body["request_id"] == "feed-123"
    assert list_response.json()["items"][0]["impression_count"] == 1


def test_view_event_counts_once_per_playback_session_after_threshold(client: TestClient) -> None:
    video = client.post("/videos", headers=_headers("owner"), json={"title": "Watched enough"}).json()
    _mark_video_ready(client, video_id=video["id"], privacy=VideoPrivacy.PUBLIC)

    too_early = client.post(
        f"/videos/{video['id']}/views",
        json={"session_id": "session-1", "position_seconds": "4.9"},
    )
    counted = client.post(
        f"/videos/{video['id']}/views",
        json={"session_id": "session-1", "position_seconds": "5.0"},
    )
    duplicate = client.post(
        f"/videos/{video['id']}/views",
        json={"session_id": "session-1", "position_seconds": "12.0"},
    )
    list_response = client.get("/videos")

    assert too_early.status_code == 202
    assert too_early.json()["counted"] is False
    assert too_early.json()["view_count"] == 0
    assert counted.status_code == 201
    assert counted.json()["counted"] is True
    assert counted.json()["view_count"] == 1
    assert duplicate.status_code == 200
    assert duplicate.json()["counted"] is False
    assert duplicate.json()["view_count"] == 1
    assert list_response.json()["items"][0]["view_count"] == 1


def test_private_video_impression_and_view_require_access(client: TestClient) -> None:
    video = client.post("/videos", headers=_headers("owner"), json={"title": "Private metrics"}).json()
    _mark_video_ready(client, video_id=video["id"], privacy=VideoPrivacy.PRIVATE)

    impression = client.post(
        f"/videos/{video['id']}/impressions",
        headers=_headers("other"),
        json={"surface": "home", "position": 0},
    )
    view = client.post(
        f"/videos/{video['id']}/views",
        headers=_headers("other"),
        json={"session_id": "session-2", "position_seconds": "10.0"},
    )
    owner_view = client.post(
        f"/videos/{video['id']}/views",
        headers=_headers("owner"),
        json={"session_id": "owner-session", "position_seconds": "10.0"},
    )

    assert impression.status_code == 403
    assert view.status_code == 403
    assert owner_view.status_code == 201
    assert owner_view.json()["view_count"] == 1
