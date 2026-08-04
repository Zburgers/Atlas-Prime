from __future__ import annotations

from contextlib import contextmanager

from media_worker.packager import PackagedRendition
from media_worker.repository import MediaRepository


class FakeCursor:
    def __init__(self, *, rowcount: int = 1, fetched: dict[str, bool] | None = None, has_fetched: bool = False) -> None:
        self.rowcount = rowcount
        self.fetched = fetched if has_fetched else {"custom_thumbnail_exists": False}

    def fetchone(self) -> dict[str, bool] | None:
        return self.fetched


class FakeConnection:
    def __init__(self, *, claimable: bool = True, updates: int = 1) -> None:
        self.calls: list[tuple[str, tuple[object, ...] | None]] = []
        self.claimable = claimable
        self.updates = updates

    @contextmanager
    def transaction(self):
        yield self

    def execute(self, query: str, params: tuple[object, ...] | None = None) -> FakeCursor:
        self.calls.append((query, params))
        if "returning job.id" in query:
            return FakeCursor(fetched={"id": "job-id"} if self.claimable else None, has_fetched=True)
        if query.lstrip().lower().startswith("select exists"):
            return FakeCursor()
        return FakeCursor(rowcount=self.updates)


def test_mark_started_claims_only_a_queued_job(monkeypatch) -> None:
    connection = FakeConnection()
    repository = MediaRepository()
    monkeypatch.setattr(repository, "_connect", lambda: _connection_context(connection))

    assert repository.mark_started(video_id="video-id", job_id="job-id", generation="generation-id", worker_id="worker") is True
    assert any("job.status = 'queued'" in query for query, _ in connection.calls)


def test_duplicate_claim_is_rejected_without_video_mutation(monkeypatch) -> None:
    connection = FakeConnection(claimable=False)
    repository = MediaRepository()
    monkeypatch.setattr(repository, "_connect", lambda: _connection_context(connection))

    assert repository.mark_started(video_id="video-id", job_id="job-id", generation="generation-id", worker_id="worker") is False
    assert len(connection.calls) == 1


def test_stage_update_is_generation_fenced(monkeypatch) -> None:
    connection = FakeConnection(updates=0)
    repository = MediaRepository()
    monkeypatch.setattr(repository, "_connect", lambda: _connection_context(connection))

    assert repository.mark_stage(video_id="video-id", job_id="job-id", generation="generation-id", stage="probing") is False
    query, params = connection.calls[0]
    assert "generation = %s" in query
    assert "status = 'running'" in query
    assert "active_processing_generation" in query
    assert params == ("probing", "job-id", "video-id", "generation-id")


def test_stale_processing_update_rolls_back_before_stage_mutation(monkeypatch) -> None:
    connection = FakeConnection(updates=0)
    repository = MediaRepository()
    monkeypatch.setattr(repository, "_connect", lambda: _connection_context(connection))

    from media_worker.packager import MediaProbe

    assert repository.mark_processing(
        video_id="video-id",
        job_id="job-id",
        generation="generation-id",
        probe=MediaProbe(duration_seconds=1.0, width=640, height=360, video_codec="h264", audio_codec="aac", source_bitrate=1000, has_audio=True),
    ) is False
    assert len(connection.calls) == 1


def test_stale_success_is_ignored(monkeypatch) -> None:
    connection = FakeConnection(claimable=True, updates=0)
    repository = MediaRepository()
    monkeypatch.setattr(repository, "_connect", lambda: _connection_context(connection))

    assert repository.mark_succeeded(
        video_id="video-id",
        job_id="job-id",
        generation="generation-id",
        master_key="master",
        thumbnail_key="thumb",
        generated_thumbnail_keys=[],
        renditions=[],
    ) is False
    assert len(connection.calls) == 1


def test_stale_failure_is_ignored(monkeypatch) -> None:
    connection = FakeConnection(updates=0)
    repository = MediaRepository()
    monkeypatch.setattr(repository, "_connect", lambda: _connection_context(connection))

    from media_worker.repository import ProcessingFailure

    assert repository.mark_failed(
        video_id="video-id",
        job_id="job-id",
        generation="generation-id",
        failure=ProcessingFailure(code="BROKEN", message="bad"),
    ) is False
    assert len(connection.calls) == 1


def test_mark_succeeded_supports_the_configured_mapping_row_factory(monkeypatch) -> None:
    connection = FakeConnection()
    repository = MediaRepository()
    monkeypatch.setattr(repository, "_connect", lambda: _connection_context(connection))

    repository.mark_succeeded(
        video_id="video-id",
        job_id="job-id",
        generation="generation-id",
        master_key="processed/video-id/hls/master.m3u8",
        thumbnail_key="processed/video-id/hls/thumbnail.jpg",
        generated_thumbnail_keys=["processed/video-id/hls/thumbnail.jpg"],
        renditions=[
            PackagedRendition(
                label="360p",
                width=640,
                    height=360,
                    target_bitrate=800000,
                    video_codec="h264",
                    segment_count=2,
                    output_size_bytes=12345,
                    playlist_storage_key="processed/video-id/hls/360p/playlist.m3u8",
            )
        ],
    )

    assert any("set status = 'ready'" in query for query, _ in connection.calls)
    assert any("set status = 'succeeded'" in query for query, _ in connection.calls)


@contextmanager
def _connection_context(connection: FakeConnection):
    yield connection
