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
def enable_test_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ATLAS_ALLOW_DEV_AUTH_HEADERS", "true")
    monkeypatch.setenv("ATLAS_ADMIN_CLERK_USER_IDS", "operator")


def _headers(user_id: str, email: str | None = None) -> dict[str, str]:
    return {
        "X-Atlas-Dev-Clerk-User-Id": user_id,
        "X-Atlas-Dev-Email": email or f"{user_id}@example.com",
    }


def _mark_video_ready(client: TestClient, video_id: str) -> None:
    import asyncio

    async def mark_ready() -> None:
        async with app.state.test_session_maker() as session:
            video = await session.get(Video, UUID(video_id))
            assert video is not None
            video.status = VideoStatus.READY.value
            video.privacy = VideoPrivacy.PUBLIC.value
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


def test_viewer_can_report_content_and_only_configured_admin_can_review_it(client: TestClient) -> None:
    video = client.post("/videos", headers=_headers("owner"), json={"title": "Reported lesson"}).json()
    _mark_video_ready(client, video["id"])

    created = client.post(
        "/moderation/reports",
        headers=_headers("viewer"),
        json={
            "target_type": "video",
            "target_id": video["id"],
            "reason": "spam",
            "details": "Repeated misleading links.",
        },
    )
    denied = client.get("/admin/reports", headers=_headers("viewer"))
    queue = client.get("/admin/reports", headers=_headers("operator"))

    assert created.status_code == 201
    assert created.json()["status"] == "open"
    assert created.json()["target_type"] == "video"
    assert denied.status_code == 403
    assert queue.status_code == 200, queue.text
    assert queue.json()["total"] == 1
    assert queue.json()["items"][0]["id"] == created.json()["id"]


def test_admin_remove_action_hides_video_from_public_surfaces_and_is_auditable(client: TestClient) -> None:
    video = client.post("/videos", headers=_headers("owner"), json={"title": "Unsafe public lesson"}).json()
    _mark_video_ready(client, video["id"])
    persisted_feed = client.get("/feed/home?request_id=moderation-removal", headers=_headers("viewer"))
    report = client.post(
        "/moderation/reports",
        headers=_headers("viewer"),
        json={"target_type": "video", "target_id": video["id"], "reason": "harmful"},
    ).json()

    action = client.post(
        f"/admin/reports/{report['id']}/actions",
        headers=_headers("operator"),
        json={"action": "remove", "reason": "Confirmed policy violation."},
    )
    public_list = client.get("/videos")
    search = client.get("/search?q=unsafe")
    feed = client.get("/feed/home?request_id=moderation-removal", headers=_headers("viewer"))
    direct_read = client.get(f"/videos/{video['id']}")
    playback = client.get(f"/videos/{video['id']}/playback")
    audit = client.get(f"/admin/audit-log?target_id={video['id']}", headers=_headers("operator"))

    assert action.status_code == 200, action.text
    assert persisted_feed.json()["items"][0]["video"]["id"] == video["id"]
    assert action.json()["report"]["status"] == "actioned"
    assert action.json()["action"]["action"] == "remove"
    assert public_list.json()["items"] == []
    assert search.json()["items"] == []
    assert feed.json()["items"] == []
    assert direct_read.status_code == 404
    assert playback.status_code == 404
    assert audit.status_code == 200
    assert audit.json()["items"][0]["action"] == "moderation.remove"


def test_viewer_can_report_comment_and_removed_comment_is_hidden(client: TestClient) -> None:
    video = client.post("/videos", headers=_headers("owner"), json={"title": "Comment review"}).json()
    _mark_video_ready(client, video["id"])
    comment = client.post(
        f"/videos/{video['id']}/comments",
        headers=_headers("author"),
        json={"body": "Abusive content"},
    ).json()
    report = client.post(
        "/moderation/reports",
        headers=_headers("viewer"),
        json={"target_type": "comment", "target_id": comment["id"], "reason": "abuse"},
    ).json()

    action = client.post(
        f"/admin/reports/{report['id']}/actions",
        headers=_headers("operator"),
        json={"action": "remove", "reason": "Confirmed abuse."},
    )
    comments = client.get(f"/videos/{video['id']}/comments")

    assert action.status_code == 200, action.text
    assert action.json()["action"]["target_type"] == "comment"
    assert comments.status_code == 200
    assert comments.json()["items"] == []
