from collections.abc import AsyncGenerator, Iterator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.deps import get_session
from app.db.base import Base
from app.db.models import Video, VideoRendition
from app.domain.status import RenditionStatus, VideoPrivacy, VideoStatus
from app.main import app
from app.services.search import _postgres_search_document


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


def test_search_returns_only_public_ready_videos(client: TestClient) -> None:
    public_video = client.post("/videos", headers=_headers("owner"), json={"title": "Needle public"}).json()
    private_video = client.post("/videos", headers=_headers("owner"), json={"title": "Needle private"}).json()
    unlisted_video = client.post("/videos", headers=_headers("owner"), json={"title": "Needle unlisted"}).json()
    public_draft = client.post("/videos", headers=_headers("owner"), json={"title": "Needle draft"}).json()

    _mark_video_ready(client, video_id=public_video["id"], privacy=VideoPrivacy.PUBLIC)
    _mark_video_ready(client, video_id=private_video["id"], privacy=VideoPrivacy.PRIVATE)
    _mark_video_ready(client, video_id=unlisted_video["id"], privacy=VideoPrivacy.UNLISTED)
    client.patch(f"/videos/{public_draft['id']}", headers=_headers("owner"), json={"privacy": "public"})

    response = client.get("/search", params={"q": "needle"}, headers=_headers("owner"))

    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "needle"
    assert body["total"] == 1
    assert [item["title"] for item in body["items"]] == ["Needle public"]
    assert body["items"][0]["thumbnail_url"] == f"/videos/{public_video['id']}/thumbnail"
    assert "thumbnail_storage_key" not in body["items"][0]
    assert "hls_master_storage_key" not in body["items"][0]


def test_search_ranks_title_matches_before_description_matches(client: TestClient) -> None:
    weaker = client.post(
        "/videos",
        headers=_headers("creator-a", "alpha@example.com"),
        json={"title": "Creator update", "description": "A deep postgres search lesson"},
    ).json()
    stronger = client.post(
        "/videos",
        headers=_headers("creator-b", "bravo@example.com"),
        json={"title": "Postgres search deep dive", "description": "Database indexing notes"},
    ).json()
    _mark_video_ready(client, video_id=weaker["id"])
    _mark_video_ready(client, video_id=stronger["id"])

    response = client.get("/search", params={"q": "postgres search"})

    assert response.status_code == 200
    titles = [item["title"] for item in response.json()["items"]]
    assert titles[:2] == ["Postgres search deep dive", "Creator update"]


def test_search_matches_channel_identity_and_handles_empty_queries(client: TestClient) -> None:
    channel = client.patch(
        "/channels/me",
        headers=_headers("search-owner", "owner@example.com"),
        json={"handle": "Data Studio", "display_name": "Data Studio"},
    ).json()
    video = client.post(
        "/videos",
        headers=_headers("search-owner", "owner@example.com"),
        json={"title": "Weekly notes", "description": "Creator log"},
    ).json()
    _mark_video_ready(client, video_id=video["id"])

    channel_response = client.get("/search", params={"q": "data studio"})
    empty_response = client.get("/search", params={"q": "   "})
    missing_response = client.get("/search", params={"q": "does-not-exist"})

    assert channel["handle"] == "data-studio"
    assert channel_response.status_code == 200
    assert [item["title"] for item in channel_response.json()["items"]] == ["Weekly notes"]
    assert empty_response.status_code == 200
    assert empty_response.json()["items"] == []
    assert empty_response.json()["total"] == 0
    assert missing_response.status_code == 200
    assert missing_response.json()["items"] == []
    assert missing_response.json()["total"] == 0


def test_postgres_search_document_uses_literal_weight_labels() -> None:
    compiled = str(select(_postgres_search_document()).compile(dialect=postgresql.dialect()))

    assert "'A'" in compiled
    assert "'B'" in compiled
    assert "'C'" in compiled
