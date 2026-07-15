from __future__ import annotations

from contextlib import contextmanager

from media_worker.packager import PackagedRendition
from media_worker.repository import MediaRepository


class FakeCursor:
    def fetchone(self) -> dict[str, bool]:
        return {"custom_thumbnail_exists": False}


class FakeConnection:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...] | None]] = []

    @contextmanager
    def transaction(self):
        yield self

    def execute(self, query: str, params: tuple[object, ...] | None = None) -> FakeCursor:
        self.calls.append((query, params))
        return FakeCursor()


def test_mark_started_claims_only_a_queued_job(monkeypatch) -> None:
    connection = FakeConnection()
    repository = MediaRepository()
    monkeypatch.setattr(repository, "_connect", lambda: _connection_context(connection))

    assert repository.mark_started(video_id="video-id", job_id="job-id", worker_id="worker") is True
    assert any("job.status = 'queued'" in query for query, _ in connection.calls)


def test_mark_succeeded_supports_the_configured_mapping_row_factory(monkeypatch) -> None:
    connection = FakeConnection()
    repository = MediaRepository()
    monkeypatch.setattr(repository, "_connect", lambda: _connection_context(connection))

    repository.mark_succeeded(
        video_id="video-id",
        job_id="job-id",
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
