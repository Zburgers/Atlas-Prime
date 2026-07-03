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


def _mark_video_ready(client: TestClient, *, video_id: str, privacy: VideoPrivacy = VideoPrivacy.PRIVATE) -> None:
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


def test_current_user_gets_default_channel_with_normalized_handle(client: TestClient) -> None:
    response = client.get("/channels/me", headers=_headers("creator-1", "Creator.Name+demo@example.com"))

    assert response.status_code == 200
    body = response.json()
    assert body["handle"] == "creator-name-demo"
    assert body["display_name"] == "Creator.Name+demo"
    assert body["owner_user_id"]

    second_response = client.get("/channels/me", headers=_headers("creator-1", "updated@example.com"))

    assert second_response.status_code == 200
    assert second_response.json()["id"] == body["id"]
    assert second_response.json()["handle"] == body["handle"]


def test_channel_handle_update_normalizes_and_rejects_duplicates(client: TestClient) -> None:
    owner = client.get("/channels/me", headers=_headers("owner", "owner@example.com")).json()
    other = client.patch(
        "/channels/me",
        headers=_headers("other", "other@example.com"),
        json={"handle": "Other Channel", "display_name": "Other Channel"},
    ).json()

    update = client.patch(
        "/channels/me",
        headers=_headers("owner", "owner@example.com"),
        json={"handle": " My Cool Channel!! ", "display_name": "My Cool Channel", "description": "Creator notes"},
    )
    duplicate = client.patch(
        "/channels/me",
        headers=_headers("owner", "owner@example.com"),
        json={"handle": other["handle"]},
    )

    assert owner["handle"] == "owner"
    assert update.status_code == 200
    assert update.json()["handle"] == "my-cool-channel"
    assert update.json()["display_name"] == "My Cool Channel"
    assert update.json()["description"] == "Creator notes"
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"]["message"] == "Channel handle is already taken"


def test_public_channel_read_lists_only_public_ready_videos(client: TestClient) -> None:
    channel = client.get("/channels/me", headers=_headers("owner", "owner@example.com")).json()
    public_video = client.post("/videos", headers=_headers("owner", "owner@example.com"), json={"title": "Public ready"}).json()
    private_video = client.post("/videos", headers=_headers("owner", "owner@example.com"), json={"title": "Private ready"}).json()
    public_draft = client.post("/videos", headers=_headers("owner", "owner@example.com"), json={"title": "Public draft"}).json()
    _mark_video_ready(client, video_id=public_video["id"], privacy=VideoPrivacy.PUBLIC)
    _mark_video_ready(client, video_id=private_video["id"], privacy=VideoPrivacy.PRIVATE)
    client.patch(f"/videos/{public_draft['id']}", headers=_headers("owner"), json={"privacy": "public"})

    response = client.get(f"/channels/{channel['handle']}")

    assert response.status_code == 200
    body = response.json()
    assert body["handle"] == "owner"
    assert [item["title"] for item in body["videos"]] == ["Public ready"]
    assert body["videos"][0]["channel_handle"] == "owner"
    assert body["videos"][0]["channel_display_name"] == "owner"
