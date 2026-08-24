from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Iterator
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.deps import get_original_storage, get_processed_hls_storage
from app.db.base import Base
from app.db.models import User, Video, VideoProcessingJob
from app.db.session import get_session
from app.domain.status import DeletionStatus, JobStatus, ProcessingStage, VideoStatus
from app.main import app
from app.services import videos as video_service


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
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

    asyncio.run(create_schema())
    app.dependency_overrides[get_session] = override_session
    app.state.test_session_maker = session_maker
    monkeypatch.setattr(video_service, "SessionLocal", session_maker)
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


class FakeOriginalStorage:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.deleted: list[str] = []

    def delete_original(self, *, key: str) -> None:
        self.deleted.append(key)
        if self.fail:
            raise RuntimeError("fake original failure")


class FakeProcessedStorage:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.deleted: list[UUID] = []

    def delete_video_tree(self, *, video_id: UUID) -> int:
        self.deleted.append(video_id)
        if self.fail:
            raise RuntimeError("fake processed failure")
        return 3


def _install_storage_fakes(original: FakeOriginalStorage, processed: FakeProcessedStorage) -> None:
    app.dependency_overrides[get_original_storage] = lambda: original
    app.dependency_overrides[get_processed_hls_storage] = lambda: processed


def _create_video(client: TestClient, *, owner: str = "owner") -> str:
    response = client.post("/videos", headers=_headers(owner), json={"title": "Deletion candidate"})
    assert response.status_code == 201
    return response.json()["id"]


async def _set_processing_state(
    session: AsyncSession,
    video_id: str,
    *,
    status: VideoStatus,
    job_status: JobStatus | None = None,
) -> UUID:
    video = await session.get(Video, UUID(video_id))
    assert video is not None
    generation = uuid4()
    video.status = status.value
    video.active_processing_generation = generation
    video.original_storage_key = f"originals/{video_id}/source.mp4"
    if job_status is not None:
        session.add(
            VideoProcessingJob(
                video_id=video.id,
                generation=generation,
                status=job_status.value,
                stage=ProcessingStage.PROBING.value if job_status == JobStatus.RUNNING else ProcessingStage.QUEUED.value,
            )
        )
    await session.commit()
    return generation


@pytest.mark.parametrize(
    ("video_status", "job_status"),
    [
        (VideoStatus.QUEUED, JobStatus.QUEUED),
        (VideoStatus.PROCESSING, JobStatus.RUNNING),
        (VideoStatus.UPLOADING, None),
    ],
)
def test_delete_tombstones_before_processing_can_continue(
    client: TestClient,
    video_status: VideoStatus,
    job_status: JobStatus | None,
) -> None:
    video_id = _create_video(client)
    original = FakeOriginalStorage()
    processed = FakeProcessedStorage()
    _install_storage_fakes(original, processed)

    async def arrange() -> None:
        async with app.state.test_session_maker() as session:
            await _set_processing_state(session, video_id, status=video_status, job_status=job_status)

    asyncio.run(arrange())
    response = client.delete(f"/videos/{video_id}", headers=_headers())

    assert response.status_code == 202
    assert response.json() == {"video_id": video_id, "deletion_status": "pending"}
    assert original.deleted == [f"originals/{video_id}/source.mp4"]
    assert processed.deleted == [UUID(video_id)]

    async def assert_state() -> None:
        async with app.state.test_session_maker() as session:
            video = await session.get(Video, UUID(video_id))
            assert video is not None
            assert video.deleted_at is not None
            assert video.active_processing_generation is None
            assert video.status == video_status.value
            if job_status is not None:
                job = await session.scalar(select(VideoProcessingJob).where(VideoProcessingJob.video_id == video.id))
                assert job is not None
                assert job.status == JobStatus.CANCELED.value
                assert job.error_code == "VIDEO_DELETED"

    asyncio.run(assert_state())


def test_delete_hides_tombstoned_video_from_reads_and_mutations(client: TestClient) -> None:
    video_id = _create_video(client)
    original = FakeOriginalStorage()
    processed = FakeProcessedStorage()
    _install_storage_fakes(original, processed)

    async def arrange() -> None:
        async with app.state.test_session_maker() as session:
            video = await session.get(Video, UUID(video_id))
            assert video is not None
            video.status = VideoStatus.READY.value
            video.privacy = "public"
            await session.commit()

    asyncio.run(arrange())
    assert client.delete(f"/videos/{video_id}", headers=_headers()).status_code == 202

    assert client.get(f"/videos/{video_id}").status_code == 404
    assert client.get(f"/videos/{video_id}/playback").status_code == 404
    assert client.get(f"/videos/{video_id}/processing-status", headers=_headers()).status_code == 404
    assert client.patch(f"/videos/{video_id}", headers=_headers(), json={"title": "resurrect"}).status_code == 404
    assert client.post(f"/videos/{video_id}/process", headers=_headers()).status_code == 404
    assert (
        client.post(
            f"/videos/{video_id}/upload",
            headers=_headers(),
            files={"file": ("lesson.mp4", b"not-a-video", "video/mp4")},
        ).status_code
        == 404
    )
    assert client.get("/videos").json()["items"] == []


def test_delete_finalize_fence_cannot_ready_or_resurrect_tombstone(client: TestClient) -> None:
    video_id = _create_video(client)
    original = FakeOriginalStorage()
    processed = FakeProcessedStorage()
    _install_storage_fakes(original, processed)

    async def arrange() -> UUID:
        async with app.state.test_session_maker() as session:
            return await _set_processing_state(
                session,
                video_id,
                status=VideoStatus.PROCESSING,
                job_status=JobStatus.RUNNING,
            )

    generation = asyncio.run(arrange())
    assert client.delete(f"/videos/{video_id}", headers=_headers()).status_code == 202

    async def attempt_finalize() -> None:
        async with app.state.test_session_maker() as session:
            result = await session.execute(
                update(Video)
                .where(
                    Video.id == UUID(video_id),
                    Video.deleted_at.is_(None),
                    Video.active_processing_generation == generation,
                )
                .values(status=VideoStatus.READY.value, hls_master_storage_key="processed/should-not-publish")
            )
            assert result.rowcount == 0
            await session.commit()

    asyncio.run(attempt_finalize())
    assert client.get(f"/videos/{video_id}").status_code == 404


def test_cleanup_failure_preserves_retryable_tombstone_and_reconciliation_completes(client: TestClient) -> None:
    video_id = _create_video(client)
    original = FakeOriginalStorage(fail=True)
    processed = FakeProcessedStorage(fail=True)

    async def tombstone() -> None:
        async with app.state.test_session_maker() as session:
            video = await session.scalar(select(Video).where(Video.id == UUID(video_id)))
            owner = await session.scalar(select(User).where(User.clerk_user_id == "owner"))
            assert video is not None and owner is not None
            video.original_storage_key = f"originals/{video_id}/source.mp4"
            video.hls_master_storage_key = f"processed/{video_id}/attempts/old/hls/master.m3u8"
            await session.commit()
            result = await video_service.delete_video(session, owner, video.id)
            assert result.deletion_status == DeletionStatus.PENDING.value

    asyncio.run(tombstone())
    assert asyncio.run(
        video_service.cleanup_deleted_video(
            UUID(video_id),
            original,
            processed,
            session_factory=app.state.test_session_maker,
        )
    ) == DeletionStatus.FAILED.value

    async def failed_state() -> Video:
        async with app.state.test_session_maker() as session:
            video = await session.get(Video, UUID(video_id))
            assert video is not None
            return video

    video = asyncio.run(failed_state())
    assert video.deleted_at is not None
    assert video.active_processing_generation is None
    assert video.deletion_status == DeletionStatus.FAILED.value
    assert video.deletion_error == "Storage cleanup failed; retry reconciliation"
    assert video.original_storage_key == f"originals/{video_id}/source.mp4"

    original.fail = False
    processed.fail = False
    assert asyncio.run(
        video_service.cleanup_deleted_video(
            UUID(video_id),
            original,
            processed,
            session_factory=app.state.test_session_maker,
        )
    ) == DeletionStatus.COMPLETE.value
    assert asyncio.run(
        video_service.cleanup_deleted_video(
            UUID(video_id),
            original,
            processed,
            session_factory=app.state.test_session_maker,
        )
    ) is None

    video = asyncio.run(failed_state())
    assert video.deletion_status == DeletionStatus.COMPLETE.value
    assert video.deletion_error is None
    assert video.original_storage_key is None
    assert video.hls_master_storage_key is None


def test_delete_is_owner_only_and_repeat_is_idempotent(client: TestClient) -> None:
    video_id = _create_video(client)
    original = FakeOriginalStorage()
    processed = FakeProcessedStorage()
    _install_storage_fakes(original, processed)

    async def arrange() -> None:
        async with app.state.test_session_maker() as session:
            video = await session.get(Video, UUID(video_id))
            assert video is not None
            video.original_storage_key = f"originals/{video_id}/source.mp4"
            await session.commit()

    asyncio.run(arrange())

    assert client.delete(f"/videos/{video_id}", headers=_headers("other")).status_code == 403
    first = client.delete(f"/videos/{video_id}", headers=_headers())
    second = client.delete(f"/videos/{video_id}", headers=_headers())

    assert first.status_code == 202
    assert second.status_code == 202
    assert second.json() == {"video_id": video_id, "deletion_status": "complete"}
    assert original.deleted == [f"originals/{video_id}/source.mp4"]
    assert processed.deleted == [UUID(video_id)]
