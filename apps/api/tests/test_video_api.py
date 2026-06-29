from collections.abc import AsyncGenerator, Iterator
from dataclasses import dataclass
from typing import BinaryIO
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_session
from app.api.deps import get_original_storage, get_processing_queue
from app.main import app
from app.services.storage import StoredObject, original_storage_key


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
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        asyncio.run(drop_schema())


def _headers(user_id: str = "user_123", email: str = "user@example.com") -> dict[str, str]:
    return {
        "X-Atlas-Dev-Clerk-User-Id": user_id,
        "X-Atlas-Dev-Email": email,
    }


def _minimal_mp4(payload: bytes = b"atlas") -> bytes:
    return b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom" + payload


class FakeOriginalStorage:
    def __init__(self) -> None:
        self.objects: list[tuple[str, bytes, str]] = []

    def put_original(
        self,
        *,
        video_id: UUID,
        extension: str,
        body: BinaryIO,
        size_bytes: int,
        content_type: str,
    ) -> StoredObject:
        key = original_storage_key(video_id, extension)
        data = body.read()
        assert len(data) == size_bytes
        self.objects.append((key, data, content_type))
        return StoredObject(bucket="test-originals", key=key, size_bytes=size_bytes, content_type=content_type)


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
        return "task-123"


def _install_upload_fakes(client: TestClient) -> tuple[FakeOriginalStorage, FakeProcessingQueue]:
    storage = FakeOriginalStorage()
    queue = FakeProcessingQueue()
    app.dependency_overrides[get_original_storage] = lambda: storage
    app.dependency_overrides[get_processing_queue] = lambda: queue
    return storage, queue


@pytest.fixture(autouse=True)
def enable_dev_auth_headers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ATLAS_ALLOW_DEV_AUTH_HEADERS", "true")


def test_create_video_defaults_to_private_draft(client: TestClient) -> None:
    response = client.post("/videos", headers=_headers(), json={"title": "First lesson"})

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "First lesson"
    assert body["privacy"] == "private"
    assert body["status"] == "draft"
    assert body["owner_id"]


def test_private_video_is_owner_only(client: TestClient) -> None:
    created = client.post("/videos", headers=_headers("owner"), json={"title": "Private cut"})
    video_id = created.json()["id"]

    owner_response = client.get(f"/videos/{video_id}", headers=_headers("owner"))
    other_response = client.get(f"/videos/{video_id}", headers=_headers("other"))

    assert owner_response.status_code == 200
    assert other_response.status_code == 403


def test_auth_required_without_clerk_token_or_enabled_dev_header(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ATLAS_ALLOW_DEV_AUTH_HEADERS", "false")

    missing = client.get("/me")
    dev_header = client.get("/me", headers=_headers("dev-user"))

    assert missing.status_code == 401
    assert missing.json()["detail"]["error"] == "Unauthorized"
    assert dev_header.status_code == 401
    assert dev_header.json()["detail"]["message"] == "Development auth headers are disabled"


def test_authorization_bearer_token_maps_to_current_user(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ATLAS_ALLOW_DEV_AUTH_HEADERS", "false")

    @dataclass(frozen=True)
    class StubClaims:
        clerk_user_id: str
        email: str | None = None

    async def verify_stub(token: str) -> StubClaims:
        assert token == "valid-session-token"
        return StubClaims(clerk_user_id="user_token", email="token@example.com")

    monkeypatch.setattr("app.api.deps.verify_clerk_session_token", verify_stub)

    response = client.get("/me", headers={"Authorization": "Bearer valid-session-token"})

    assert response.status_code == 200
    assert response.json()["clerk_user_id"] == "user_token"
    assert response.json()["email"] == "token@example.com"


def test_processing_status_reports_draft_without_job(client: TestClient) -> None:
    created = client.post("/videos", headers=_headers(), json={"title": "Needs upload"})
    video_id = created.json()["id"]

    response = client.get(f"/videos/{video_id}/processing-status", headers=_headers())

    assert response.status_code == 200
    assert response.json() == {
        "video_id": video_id,
        "video_status": "draft",
        "latest_job": None,
        "failure_code": None,
        "failure_message": None,
    }


def test_process_requires_uploaded_state(client: TestClient) -> None:
    created = client.post("/videos", headers=_headers(), json={"title": "Not uploaded"})
    video_id = created.json()["id"]

    response = client.post(f"/videos/{video_id}/process", headers=_headers())

    assert response.status_code == 409
    assert response.json()["detail"]["details"]["required_status"] == "uploaded"


def test_upload_requires_video_owner(client: TestClient) -> None:
    storage, queue = _install_upload_fakes(client)
    created = client.post("/videos", headers=_headers("owner"), json={"title": "Owner only"})
    video_id = created.json()["id"]

    response = client.post(
        f"/videos/{video_id}/upload",
        headers=_headers("other"),
        files={"file": ("lesson.mp4", _minimal_mp4(), "video/mp4")},
    )

    assert response.status_code == 403
    assert storage.objects == []
    assert queue.jobs == []


def test_upload_rejects_invalid_media_and_marks_video_failed(client: TestClient) -> None:
    storage, queue = _install_upload_fakes(client)
    created = client.post("/videos", headers=_headers(), json={"title": "Bad upload"})
    video_id = created.json()["id"]

    response = client.post(
        f"/videos/{video_id}/upload",
        headers=_headers(),
        files={"file": ("lesson.mp4", b"not actually an mp4", "video/mp4")},
    )
    status_response = client.get(f"/videos/{video_id}/processing-status", headers=_headers())

    assert response.status_code == 415
    assert storage.objects == []
    assert queue.jobs == []
    assert status_response.json()["video_status"] == "failed"
    assert status_response.json()["failure_code"] == "UPLOAD_VALIDATION_FAILED"


def test_upload_rejects_oversized_file(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    storage, queue = _install_upload_fakes(client)
    monkeypatch.setenv("ATLAS_UPLOAD_MAX_BYTES", "16")
    created = client.post("/videos", headers=_headers(), json={"title": "Too large"})
    video_id = created.json()["id"]

    response = client.post(
        f"/videos/{video_id}/upload",
        headers=_headers(),
        files={"file": ("lesson.mp4", _minimal_mp4(b"x" * 64), "video/mp4")},
    )

    assert response.status_code == 413
    assert storage.objects == []
    assert queue.jobs == []


def test_upload_stores_original_and_queues_processing(client: TestClient) -> None:
    storage, queue = _install_upload_fakes(client)
    created = client.post("/videos", headers=_headers(), json={"title": "Upload me"})
    video_id = created.json()["id"]
    data = _minimal_mp4()

    response = client.post(
        f"/videos/{video_id}/upload",
        headers=_headers(),
        files={"file": ("lesson.mp4", data, "video/mp4")},
    )

    assert response.status_code == 200
    body = response.json()
    expected_key = f"originals/{video_id}/source.mp4"
    assert body["video"]["status"] == "queued"
    assert body["video"]["original_storage_key"] == expected_key
    assert body["processing_job"]["status"] == "queued"
    assert body["storage_key"] == expected_key
    assert body["size_bytes"] == len(data)
    assert body["content_type"] == "video/mp4"
    assert body["celery_task_id"] == "task-123"
    assert storage.objects == [(expected_key, data, "video/mp4")]
    assert queue.jobs == [
        {
            "video_id": video_id,
            "job_id": body["processing_job"]["id"],
            "original_storage_key": expected_key,
        }
    ]
