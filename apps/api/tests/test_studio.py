from collections.abc import AsyncGenerator, Iterator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.deps import get_processing_queue
from app.db.base import Base
from app.db.models import Video
from app.db.session import get_session
from app.domain.status import VideoPrivacy, VideoStatus
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


def _set_video_state(
    client: TestClient,
    *,
    video_id: str,
    status: VideoStatus,
    privacy: VideoPrivacy = VideoPrivacy.PRIVATE,
    original_storage_key: str | None = None,
) -> None:
    import asyncio

    async def set_state() -> None:
        async with app.state.test_session_maker() as session:
            video = await session.get(Video, UUID(video_id))
            assert video is not None
            video.status = status.value
            video.privacy = privacy.value
            video.original_storage_key = original_storage_key
            if status == VideoStatus.FAILED:
                video.failure_code = "MEDIA_COMMAND_FAILED"
                video.failure_message = "Processing failed"
            await session.commit()

    asyncio.run(set_state())


class FakeProcessingQueue:
    def __init__(self) -> None:
        self.jobs: list[dict[str, str]] = []

    def enqueue_video_processing(self, *, video_id: UUID, job_id: UUID, original_storage_key: str) -> str:
        self.jobs.append(
            {
                "video_id": str(video_id),
                "job_id": str(job_id),
                "original_storage_key": original_storage_key,
            }
        )
        return "retry-task-123"


def test_studio_lists_only_owned_videos_with_filters(client: TestClient) -> None:
    own_ready = client.post("/videos", headers=_headers("owner"), json={"title": "Own ready"}).json()
    own_failed = client.post("/videos", headers=_headers("owner"), json={"title": "Own failed"}).json()
    other_ready = client.post("/videos", headers=_headers("other"), json={"title": "Other ready"}).json()
    _set_video_state(client, video_id=own_ready["id"], status=VideoStatus.READY, privacy=VideoPrivacy.PUBLIC)
    _set_video_state(client, video_id=own_failed["id"], status=VideoStatus.FAILED)
    _set_video_state(client, video_id=other_ready["id"], status=VideoStatus.READY, privacy=VideoPrivacy.PUBLIC)

    all_response = client.get("/studio/videos", headers=_headers("owner"))
    failed_response = client.get("/studio/videos?status=failed", headers=_headers("owner"))
    public_response = client.get("/studio/videos?privacy=public", headers=_headers("owner"))

    assert all_response.status_code == 200
    assert {item["title"] for item in all_response.json()["items"]} == {"Own ready", "Own failed"}
    assert failed_response.status_code == 200
    assert [item["title"] for item in failed_response.json()["items"]] == ["Own failed"]
    assert public_response.status_code == 200
    assert [item["title"] for item in public_response.json()["items"]] == ["Own ready"]


def test_studio_edit_is_owner_only(client: TestClient) -> None:
    video = client.post("/videos", headers=_headers("owner"), json={"title": "Before"}).json()

    denied = client.patch(
        f"/studio/videos/{video['id']}",
        headers=_headers("other"),
        json={"title": "Stolen", "privacy": "public"},
    )
    edited = client.patch(
        f"/studio/videos/{video['id']}",
        headers=_headers("owner"),
        json={"title": "After", "description": "Studio edit", "privacy": "unlisted"},
    )

    assert denied.status_code == 403
    assert edited.status_code == 200
    assert edited.json()["title"] == "After"
    assert edited.json()["description"] == "Studio edit"
    assert edited.json()["privacy"] == "unlisted"


def test_studio_retries_failed_video_only_when_safe(client: TestClient) -> None:
    queue = FakeProcessingQueue()
    app.dependency_overrides[get_processing_queue] = lambda: queue
    failed = client.post("/videos", headers=_headers("owner"), json={"title": "Retry me"}).json()
    draft = client.post("/videos", headers=_headers("owner"), json={"title": "Draft"}).json()
    missing_original = client.post("/videos", headers=_headers("owner"), json={"title": "Missing original"}).json()
    original_key = f"originals/{failed['id']}/source.mp4"
    _set_video_state(
        client,
        video_id=failed["id"],
        status=VideoStatus.FAILED,
        original_storage_key=original_key,
    )
    _set_video_state(client, video_id=missing_original["id"], status=VideoStatus.FAILED)

    other_response = client.post(f"/studio/videos/{failed['id']}/retry-processing", headers=_headers("other"))
    draft_response = client.post(f"/studio/videos/{draft['id']}/retry-processing", headers=_headers("owner"))
    missing_response = client.post(
        f"/studio/videos/{missing_original['id']}/retry-processing",
        headers=_headers("owner"),
    )
    retried = client.post(f"/studio/videos/{failed['id']}/retry-processing", headers=_headers("owner"))
    status_response = client.get(f"/videos/{failed['id']}/processing-status", headers=_headers("owner"))

    assert other_response.status_code == 403
    assert draft_response.status_code == 409
    assert missing_response.status_code == 409
    assert retried.status_code == 201
    assert retried.json()["status"] == "queued"
    assert queue.jobs == [
        {
            "video_id": failed["id"],
            "job_id": retried.json()["id"],
            "original_storage_key": original_key,
        }
    ]
    assert status_response.json()["video_status"] == "queued"
    assert status_response.json()["failure_code"] is None


def test_owner_can_replace_ordered_chapters(client: TestClient) -> None:
    video = client.post("/videos", headers=_headers("owner"), json={"title": "Chaptered lesson"}).json()

    replaced = client.put(
        f"/studio/videos/{video['id']}/chapters",
        headers=_headers("owner"),
        json={
            "items": [
                {"title": "Introduction", "start_seconds": 0},
                {"title": "Practice", "start_seconds": 42.5},
            ]
        },
    )
    listed = client.get(f"/studio/videos/{video['id']}/chapters", headers=_headers("owner"))
    denied = client.get(f"/studio/videos/{video['id']}/chapters", headers=_headers("other"))
    _set_video_state(client, video_id=video["id"], status=VideoStatus.READY)
    playback = client.get(f"/videos/{video['id']}/playback", headers=_headers("owner"))

    assert replaced.status_code == 200
    assert replaced.json()["items"] == [
        {"title": "Introduction", "start_seconds": "0.000"},
        {"title": "Practice", "start_seconds": "42.500"},
    ]
    assert listed.json() == replaced.json()
    assert denied.status_code == 403
    assert playback.json()["chapters"] == replaced.json()["items"]


def test_owner_can_view_processing_timeline(client: TestClient) -> None:
    queue = FakeProcessingQueue()
    app.dependency_overrides[get_processing_queue] = lambda: queue
    video = client.post("/videos", headers=_headers("owner"), json={"title": "Timeline"}).json()
    _set_video_state(
        client,
        video_id=video["id"],
        status=VideoStatus.FAILED,
        original_storage_key=f"originals/{video['id']}/source.mp4",
    )
    client.post(f"/studio/videos/{video['id']}/retry-processing", headers=_headers("owner"))

    response = client.get(f"/studio/videos/{video['id']}/processing-timeline", headers=_headers("owner"))
    denied = client.get(f"/studio/videos/{video['id']}/processing-timeline", headers=_headers("other"))

    assert response.status_code == 200
    assert response.json()["items"][-1]["status"] == "queued"
    assert response.json()["items"][-1]["stage"] == "queued"
    assert denied.status_code == 403


def test_owner_can_rotate_playback_tokens(client: TestClient) -> None:
    video = client.post("/videos", headers=_headers("owner"), json={"title": "Rotate playback"}).json()

    rotated = client.post(f"/studio/videos/{video['id']}/rotate-playback-token", headers=_headers("owner"))
    denied = client.post(f"/studio/videos/{video['id']}/rotate-playback-token", headers=_headers("other"))

    assert rotated.status_code == 200
    assert rotated.json() == {"playback_token_version": 2}
    assert denied.status_code == 403
