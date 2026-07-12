from collections.abc import AsyncGenerator, Iterator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.deps import get_processed_hls_storage, get_session
from app.db.base import Base
from app.db.models import Video
from app.domain.status import VideoStatus
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


def _headers(user_id: str = "owner", email: str = "owner@example.com") -> dict[str, str]:
    return {
        "X-Atlas-Dev-Clerk-User-Id": user_id,
        "X-Atlas-Dev-Email": email,
    }


def _mark_video_ready(client: TestClient, video_id: str) -> None:
    import asyncio

    async def mark_ready() -> None:
        async with app.state.test_session_maker() as session:
            video = await session.get(Video, UUID(video_id))
            assert video is not None
            video.status = VideoStatus.READY.value
            video.hls_master_storage_key = f"processed/{video_id}/hls/master.m3u8"
            await session.commit()

    asyncio.run(mark_ready())


def test_owner_can_upload_a_custom_thumbnail_without_receiving_storage_keys(client: TestClient) -> None:
    class FakeStorage:
        def put_thumbnail(self, *, key: str, body, content_type: str) -> None:
            return None

    app.dependency_overrides[get_processed_hls_storage] = lambda: FakeStorage()
    video = client.post("/videos", headers=_headers(), json={"title": "Thumbnail target"}).json()
    _mark_video_ready(client, video["id"])

    response = client.post(
        f"/studio/videos/{video['id']}/thumbnails",
        headers=_headers(),
        files={"file": ("cover.png", _png(640, 360), "image/png")},
    )
    playback = client.get(f"/videos/{video['id']}/playback", headers=_headers())

    assert response.status_code == 201
    body = response.json()
    assert body["source"] == "custom"
    assert body["selected"] is True
    assert body["url"] == f"/videos/{video['id']}/thumbnail"
    assert "storage_key" not in body
    assert playback.json()["thumbnail_url"] == f"/videos/{video['id']}/thumbnail"


def _png(width: int, height: int) -> bytes:
    return b"\x89PNG\r\n\x1a\n" + (13).to_bytes(4, "big") + b"IHDR" + width.to_bytes(4, "big") + height.to_bytes(4, "big") + b"\x08\x02\x00\x00\x00"
