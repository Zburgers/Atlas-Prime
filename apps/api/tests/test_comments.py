from collections.abc import AsyncGenerator, Iterator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import Video, VideoRendition
from app.db.session import get_session
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


def test_public_users_can_read_comments_on_public_video(client: TestClient) -> None:
    video = client.post("/videos", headers=_headers("owner"), json={"title": "Public comments"}).json()
    _mark_video_ready(client, video_id=video["id"], privacy=VideoPrivacy.PUBLIC)
    created = client.post(
        f"/videos/{video['id']}/comments",
        headers=_headers("viewer", "viewer@example.com"),
        json={"body": "First comment"},
    )

    response = client.get(f"/videos/{video['id']}/comments")

    assert created.status_code == 201
    assert created.json()["body"] == "First comment"
    assert created.json()["author_display_name"] == "Atlas viewer"
    assert "viewer@example.com" not in created.text
    assert created.json()["owned_by_current_user"] is True
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["body"] == "First comment"
    assert response.json()["items"][0]["author_display_name"] == "Atlas viewer"
    assert response.json()["items"][0]["owned_by_current_user"] is False


def test_signed_in_user_can_comment_on_accessible_private_video(client: TestClient) -> None:
    video = client.post("/videos", headers=_headers("owner"), json={"title": "Private comments"}).json()
    _mark_video_ready(client, video_id=video["id"], privacy=VideoPrivacy.PRIVATE)

    owner_comment = client.post(
        f"/videos/{video['id']}/comments",
        headers=_headers("owner", "owner@example.com"),
        json={"body": "Owner note"},
    )
    owner_list = client.get(f"/videos/{video['id']}/comments", headers=_headers("owner"))
    other_comment = client.post(f"/videos/{video['id']}/comments", headers=_headers("other"), json={"body": "nope"})
    public_list = client.get(f"/videos/{video['id']}/comments")

    assert owner_comment.status_code == 201
    assert owner_list.status_code == 200
    assert [item["body"] for item in owner_list.json()["items"]] == ["Owner note"]
    assert other_comment.status_code == 403
    assert public_list.status_code == 403


def test_comment_delete_is_limited_to_author(client: TestClient) -> None:
    video = client.post("/videos", headers=_headers("owner"), json={"title": "Delete comments"}).json()
    _mark_video_ready(client, video_id=video["id"], privacy=VideoPrivacy.PUBLIC)
    created = client.post(
        f"/videos/{video['id']}/comments",
        headers=_headers("author"),
        json={"body": "Remove me"},
    ).json()

    denied = client.delete(f"/comments/{created['id']}", headers=_headers("other"))
    removed = client.delete(f"/comments/{created['id']}", headers=_headers("author"))
    listed = client.get(f"/videos/{video['id']}/comments")

    assert denied.status_code == 403
    assert removed.status_code == 204
    assert listed.status_code == 200
    assert listed.json()["items"] == []
