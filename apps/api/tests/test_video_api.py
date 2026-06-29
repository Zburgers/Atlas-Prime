from collections.abc import AsyncGenerator, Iterator
from dataclasses import dataclass
from typing import BinaryIO
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import Video, VideoRendition
from app.db.session import get_session
from app.api.deps import get_original_storage, get_processed_hls_storage, get_processing_queue
from app.domain.status import RenditionStatus, VideoPrivacy, VideoStatus
from app.main import app
from app.services.processing_queue import QueueInspection, WorkerInspection
from app.services.storage import HlsObject, HlsObjectNotFoundError, StoredObject, original_storage_key


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

    def inspect_workers(self, *, timeout: float = 1.0) -> WorkerInspection:
        return WorkerInspection(
            ok=True,
            online_workers=["celery@worker-test"],
            active_queues={"celery@worker-test": ["media"]},
        )

    def inspect_queue(self) -> QueueInspection:
        return QueueInspection(ok=True, media_queue_depth=len(self.jobs))


class FakeProcessedHlsStorage:
    def __init__(self, objects: dict[str, tuple[bytes, str]] | None = None) -> None:
        self.objects = objects or {}
        self.requests: list[str] = []

    def get_hls_object(self, *, key: str) -> HlsObject:
        self.requests.append(key)
        try:
            body, content_type = self.objects[key]
        except KeyError:
            raise HlsObjectNotFoundError(key)
        return HlsObject(
            key=key,
            body=body,
            content_type=content_type,
            content_length=len(body),
            etag='"test-etag"',
        )


def _install_upload_fakes(client: TestClient) -> tuple[FakeOriginalStorage, FakeProcessingQueue]:
    storage = FakeOriginalStorage()
    queue = FakeProcessingQueue()
    app.dependency_overrides[get_original_storage] = lambda: storage
    app.dependency_overrides[get_processing_queue] = lambda: queue
    return storage, queue


def _install_hls_fake(storage: FakeProcessedHlsStorage) -> None:
    app.dependency_overrides[get_processed_hls_storage] = lambda: storage


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


def test_playback_metadata_and_hls_master_are_served_for_owner(client: TestClient) -> None:
    created = client.post("/videos", headers=_headers("owner"), json={"title": "Ready"})
    video_id = created.json()["id"]
    _mark_video_ready(client, video_id=video_id)
    master_key = f"processed/{video_id}/hls/master.m3u8"
    storage = FakeProcessedHlsStorage({master_key: (b"#EXTM3U\n", "application/vnd.apple.mpegurl")})
    _install_hls_fake(storage)

    metadata = client.get(f"/videos/{video_id}/playback", headers=_headers("owner"))
    response = client.get(f"/videos/{video_id}/hls/master.m3u8", headers=_headers("owner"))

    assert metadata.status_code == 200
    assert metadata.json()["master_playlist_url"] == f"/videos/{video_id}/hls/master.m3u8"
    assert response.status_code == 200
    assert response.content == b"#EXTM3U\n"
    assert response.headers["content-type"].startswith("application/vnd.apple.mpegurl")
    assert response.headers["cache-control"] == "private, no-cache"
    assert response.headers["etag"] == '"test-etag"'
    assert storage.requests == [master_key]


def test_hls_segment_uses_immutable_cache_headers(client: TestClient) -> None:
    created = client.post("/videos", headers=_headers("owner"), json={"title": "Ready segment"})
    video_id = created.json()["id"]
    _mark_video_ready(client, video_id=video_id)
    segment_key = f"processed/{video_id}/hls/360p/segment_000.ts"
    storage = FakeProcessedHlsStorage({segment_key: (b"segment-data", "video/mp2t")})
    _install_hls_fake(storage)

    response = client.get(f"/videos/{video_id}/hls/360p/segment_000.ts", headers=_headers("owner"))

    assert response.status_code == 200
    assert response.content == b"segment-data"
    assert response.headers["content-type"].startswith("video/mp2t")
    assert response.headers["cache-control"] == "private, max-age=31536000, immutable"
    assert storage.requests == [segment_key]


def test_private_hls_asset_is_denied_to_non_owner_before_storage_read(client: TestClient) -> None:
    created = client.post("/videos", headers=_headers("owner"), json={"title": "Private ready"})
    video_id = created.json()["id"]
    _mark_video_ready(client, video_id=video_id)
    storage = FakeProcessedHlsStorage()
    _install_hls_fake(storage)

    response = client.get(f"/videos/{video_id}/hls/master.m3u8", headers=_headers("other"))

    assert response.status_code == 403
    assert storage.requests == []


def test_public_hls_asset_can_be_served_without_identity(client: TestClient) -> None:
    created = client.post("/videos", headers=_headers("owner"), json={"title": "Public ready"})
    video_id = created.json()["id"]
    _mark_video_ready(client, video_id=video_id, privacy=VideoPrivacy.PUBLIC)
    thumbnail_key = f"processed/{video_id}/hls/thumbnail.jpg"
    storage = FakeProcessedHlsStorage({thumbnail_key: (b"jpg", "image/jpeg")})
    _install_hls_fake(storage)

    response = client.get(f"/videos/{video_id}/hls/thumbnail.jpg")

    assert response.status_code == 200
    assert response.content == b"jpg"
    assert response.headers["content-type"].startswith("image/jpeg")
    assert response.headers["cache-control"] == "private, max-age=300"
    assert storage.requests == [thumbnail_key]


def test_hls_path_traversal_is_rejected_before_storage_read(client: TestClient) -> None:
    created = client.post("/videos", headers=_headers("owner"), json={"title": "Traversal"})
    video_id = created.json()["id"]
    _mark_video_ready(client, video_id=video_id)
    storage = FakeProcessedHlsStorage()
    _install_hls_fake(storage)

    response = client.get(f"/videos/{video_id}/hls/%2e%2e/secret.txt", headers=_headers("owner"))

    assert response.status_code == 400
    assert response.json()["detail"]["message"] == "Invalid HLS asset path"
    assert storage.requests == []


def test_hls_unknown_allowed_asset_returns_404(client: TestClient) -> None:
    created = client.post("/videos", headers=_headers("owner"), json={"title": "Missing object"})
    video_id = created.json()["id"]
    _mark_video_ready(client, video_id=video_id)
    storage = FakeProcessedHlsStorage()
    _install_hls_fake(storage)

    response = client.get(f"/videos/{video_id}/hls/360p/segment_999.ts", headers=_headers("owner"))

    assert response.status_code == 404
    assert response.json()["detail"]["message"] == "HLS asset not found"
    assert storage.requests == [f"processed/{video_id}/hls/360p/segment_999.ts"]


def test_playback_event_is_recorded_for_accessible_video(client: TestClient) -> None:
    created = client.post("/videos", headers=_headers("owner"), json={"title": "Observable playback"})
    video_id = created.json()["id"]
    _mark_video_ready(client, video_id=video_id)

    response = client.post(
        f"/videos/{video_id}/events",
        headers=_headers("owner"),
        json={
            "event_type": "error",
            "position_seconds": "1.25",
            "quality_label": "manifestLoadError",
            "client_timestamp": "2026-06-29T12:00:00Z",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["video_id"] == video_id
    assert body["event_type"] == "error"
    assert body["quality_label"] == "manifestLoadError"


def test_admin_ops_reports_worker_and_queue_health(client: TestClient) -> None:
    _storage, queue = _install_upload_fakes(client)

    response = client.get("/admin/ops", headers=_headers("operator"))

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["worker"]["online_workers"] == ["celery@worker-test"]
    assert body["redis"]["media_queue_depth"] == len(queue.jobs)


def test_admin_jobs_include_video_failure_context(client: TestClient) -> None:
    _install_upload_fakes(client)
    created = client.post("/videos", headers=_headers("owner"), json={"title": "Bad observable upload"})
    video_id = created.json()["id"]
    client.post(
        f"/videos/{video_id}/upload",
        headers=_headers("owner"),
        files={"file": ("lesson.mp4", b"not actually an mp4", "video/mp4")},
    )

    response = client.get("/admin/jobs", headers=_headers("operator"))

    assert response.status_code == 200
    assert response.json() == []
    debug = client.get(f"/admin/videos/{video_id}/debug", headers=_headers("operator"))
    assert debug.status_code == 200
    assert debug.json()["video"]["failure_code"] == "UPLOAD_VALIDATION_FAILED"


def test_admin_debug_includes_jobs_renditions_and_playback_events(client: TestClient) -> None:
    _install_upload_fakes(client)
    created = client.post("/videos", headers=_headers("owner"), json={"title": "Ready debug"})
    video_id = created.json()["id"]
    upload = client.post(
        f"/videos/{video_id}/upload",
        headers=_headers("owner"),
        files={"file": ("lesson.mp4", _minimal_mp4(), "video/mp4")},
    )
    _mark_video_ready(client, video_id=video_id)
    client.post(
        f"/videos/{video_id}/events",
        headers=_headers("owner"),
        json={"event_type": "player_ready", "quality_label": "hls.js"},
    )

    jobs = client.get("/admin/jobs", headers=_headers("operator"))
    debug = client.get(f"/admin/videos/{video_id}/debug", headers=_headers("operator"))

    assert upload.status_code == 200
    assert jobs.status_code == 200
    assert jobs.json()[0]["video_title"] == "Ready debug"
    assert jobs.json()[0]["video_status"] == "ready"
    assert debug.status_code == 200
    body = debug.json()
    assert body["video"]["id"] == video_id
    assert body["processing_jobs"][0]["status"] == "queued"
    assert body["renditions"][0]["label"] == "360p"
    assert body["recent_playback_events"][0]["event_type"] == "player_ready"
