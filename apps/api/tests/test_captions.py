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
from app.services.storage import HlsObject, HlsObjectNotFoundError


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


def _headers(user_id: str = "owner") -> dict[str, str]:
    return {
        "X-Atlas-Dev-Clerk-User-Id": user_id,
        "X-Atlas-Dev-Email": f"{user_id}@example.com",
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


def test_owner_can_upload_webvtt_caption_and_playback_exposes_api_owned_track_url(client: TestClient) -> None:
    class FakeStorage:
        def __init__(self) -> None:
            self.objects: dict[str, bytes] = {}

        def put_caption(self, *, key: str, body, content_type: str) -> None:
            self.objects[key] = body.read()

        def get_caption(self, *, key: str) -> HlsObject:
            try:
                body = self.objects[key]
            except KeyError:
                raise HlsObjectNotFoundError(key)
            return HlsObject(key=key, body=body, content_type="text/vtt", content_length=len(body), etag='"caption"')

    storage = FakeStorage()
    app.dependency_overrides[get_processed_hls_storage] = lambda: storage
    video = client.post("/videos", headers=_headers(), json={"title": "Caption target"}).json()
    _mark_video_ready(client, video["id"])

    uploaded = client.post(
        f"/studio/videos/{video['id']}/captions",
        headers=_headers(),
        data={"language": "en", "label": "English"},
        files={"file": ("english.vtt", b"WEBVTT\n\n00:00.000 --> 00:02.000\nHello Atlas\n", "text/vtt")},
    )
    listed = client.get(f"/studio/videos/{video['id']}/captions", headers=_headers())
    playback = client.get(f"/videos/{video['id']}/playback", headers=_headers())

    assert uploaded.status_code == 201
    body = uploaded.json()
    assert body["language"] == "en"
    assert body["label"] == "English"
    assert body["default"] is True
    assert body["url"] == f"/videos/{video['id']}/captions/{body['id']}"
    assert "storage_key" not in body
    assert listed.json()["items"] == [body]
    assert playback.json()["text_tracks"] == [body]

    delivered = client.get(body["url"], headers=_headers())
    denied = client.get(body["url"], headers=_headers("other"))
    assert delivered.status_code == 200
    assert delivered.headers["content-type"].startswith("text/vtt")
    assert delivered.text.startswith("WEBVTT")
    assert denied.status_code == 403


def test_caption_upload_rejects_non_webvtt_content(client: TestClient) -> None:
    video = client.post("/videos", headers=_headers(), json={"title": "Invalid caption"}).json()
    _mark_video_ready(client, video["id"])

    response = client.post(
        f"/studio/videos/{video['id']}/captions",
        headers=_headers(),
        data={"language": "en", "label": "English"},
        files={"file": ("english.vtt", b"not a caption", "text/vtt")},
    )

    assert response.status_code == 415
    assert response.json()["detail"]["error"] == "UnsupportedMediaType"


def test_uploading_a_default_caption_replaces_the_previous_default(client: TestClient) -> None:
    class FakeStorage:
        def put_caption(self, *, key: str, body, content_type: str) -> None:
            body.read()

    app.dependency_overrides[get_processed_hls_storage] = FakeStorage
    video = client.post("/videos", headers=_headers(), json={"title": "Default captions"}).json()
    _mark_video_ready(client, video["id"])

    first = client.post(
        f"/studio/videos/{video['id']}/captions",
        headers=_headers(),
        data={"language": "en", "label": "English"},
        files={"file": ("english.vtt", b"WEBVTT\n", "text/vtt")},
    )
    second = client.post(
        f"/studio/videos/{video['id']}/captions",
        headers=_headers(),
        data={"language": "es", "label": "Espanol", "is_default": "true"},
        files={"file": ("spanish.vtt", b"WEBVTT\n", "text/vtt")},
    )
    listed = client.get(f"/studio/videos/{video['id']}/captions", headers=_headers())

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["default"] is True
    assert [(item["language"], item["default"]) for item in listed.json()["items"]] == [("es", True), ("en", False)]
