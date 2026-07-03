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


def test_signed_in_viewer_can_like_and_unlike_once(client: TestClient) -> None:
    video = client.post("/videos", headers=_headers("owner"), json={"title": "Likeable"}).json()
    _mark_video_ready(client, video_id=video["id"])

    created = client.post(f"/videos/{video['id']}/like", headers=_headers("viewer"))
    duplicate = client.post(f"/videos/{video['id']}/like", headers=_headers("viewer"))
    status_response = client.get(f"/videos/{video['id']}/engagement", headers=_headers("viewer"))
    listed = client.get("/videos")
    removed = client.delete(f"/videos/{video['id']}/like", headers=_headers("viewer"))
    duplicate_remove = client.delete(f"/videos/{video['id']}/like", headers=_headers("viewer"))

    assert created.status_code == 201
    assert created.json()["liked"] is True
    assert created.json()["like_count"] == 1
    assert duplicate.status_code == 200
    assert duplicate.json()["like_count"] == 1
    assert status_response.status_code == 200
    assert status_response.json()["liked"] is True
    assert status_response.json()["saved_to_watch_later"] is False
    assert listed.json()["items"][0]["like_count"] == 1
    assert removed.status_code == 200
    assert removed.json()["liked"] is False
    assert removed.json()["like_count"] == 0
    assert duplicate_remove.status_code == 200
    assert duplicate_remove.json()["like_count"] == 0


def test_signed_in_viewer_can_save_and_remove_watch_later_once(client: TestClient) -> None:
    video = client.post("/videos", headers=_headers("owner"), json={"title": "Saveable"}).json()
    _mark_video_ready(client, video_id=video["id"])

    saved = client.post(f"/videos/{video['id']}/watch-later", headers=_headers("viewer"))
    duplicate = client.post(f"/videos/{video['id']}/watch-later", headers=_headers("viewer"))
    status_response = client.get(f"/videos/{video['id']}/engagement", headers=_headers("viewer"))
    removed = client.delete(f"/videos/{video['id']}/watch-later", headers=_headers("viewer"))
    duplicate_remove = client.delete(f"/videos/{video['id']}/watch-later", headers=_headers("viewer"))

    assert saved.status_code == 201
    assert saved.json()["saved_to_watch_later"] is True
    assert duplicate.status_code == 200
    assert duplicate.json()["saved_to_watch_later"] is True
    assert status_response.status_code == 200
    assert status_response.json()["liked"] is False
    assert status_response.json()["saved_to_watch_later"] is True
    assert removed.status_code == 200
    assert removed.json()["saved_to_watch_later"] is False
    assert duplicate_remove.status_code == 200
    assert duplicate_remove.json()["saved_to_watch_later"] is False


def test_private_video_reactions_require_access(client: TestClient) -> None:
    video = client.post("/videos", headers=_headers("owner"), json={"title": "Private reactions"}).json()
    _mark_video_ready(client, video_id=video["id"], privacy=VideoPrivacy.PRIVATE)

    other_like = client.post(f"/videos/{video['id']}/like", headers=_headers("other"))
    other_save = client.post(f"/videos/{video['id']}/watch-later", headers=_headers("other"))
    owner_like = client.post(f"/videos/{video['id']}/like", headers=_headers("owner"))

    assert other_like.status_code == 403
    assert other_save.status_code == 403
    assert owner_like.status_code == 201
    assert owner_like.json()["like_count"] == 1
    assert client.get("/videos").json()["items"] == []
