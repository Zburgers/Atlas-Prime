from __future__ import annotations

from contextlib import contextmanager

from media_worker.packager import PackageResult, PackagedRendition
from media_worker.repository import MediaRepository, PublicationResult
from media_worker.storage import UploadedHlsAsset


class FakeCursor:
    def __init__(self, *, rowcount: int = 1, fetched: dict[str, object] | None = None, has_fetched: bool = False) -> None:
        self.rowcount = rowcount
        self.fetched = fetched if has_fetched else {"custom_thumbnail_exists": False}

    def fetchone(self) -> dict[str, object] | None:
        return self.fetched


class FakeConnection:
    def __init__(
        self,
        *,
        claimable: bool = True,
        updates: int = 1,
        rowcounts: list[int] | None = None,
        video_exists: bool = True,
        custom_thumbnail_exists: bool = False,
        old_master_key: str | None = "processed/video-id/attempts/old-generation/hls/master.m3u8",
    ) -> None:
        self.calls: list[tuple[str, object]] = []
        self.claimable = claimable
        self.updates = updates
        self.rowcounts = list(rowcounts or [])
        self.video_exists = video_exists
        self.custom_thumbnail_exists = custom_thumbnail_exists
        self.old_master_key = old_master_key
        self.rollbacks = 0
        self.commits = 0

    @contextmanager
    def transaction(self):
        try:
            yield self
        except BaseException:
            self.rollbacks += 1
            raise
        else:
            self.commits += 1

    def execute(self, query: str, params: tuple[object, ...] | None = None) -> FakeCursor:
        self.calls.append((query, params))
        if "returning job.id" in query:
            return FakeCursor(fetched={"id": "job-id"} if self.claimable else None, has_fetched=True)
        if "select hls_master_storage_key" in query:
            fetched = {"hls_master_storage_key": self.old_master_key} if self.video_exists else None
            return FakeCursor(fetched=fetched, has_fetched=True)
        if query.lstrip().lower().startswith("select exists"):
            return FakeCursor(fetched={"custom_thumbnail_exists": self.custom_thumbnail_exists}, has_fetched=True)
        rowcount = self.rowcounts.pop(0) if self.rowcounts else self.updates
        return FakeCursor(rowcount=rowcount)

    def executemany(self, query: str, params_seq: list[tuple[object, ...]]) -> None:
        self.calls.append((query, params_seq))


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


def test_started_second_fence_rolls_back_first_claim(monkeypatch) -> None:
    connection = FakeConnection(rowcounts=[0])
    repository = MediaRepository()
    monkeypatch.setattr(repository, "_connect", lambda: _connection_context(connection))

    assert repository.mark_started(video_id="video-id", job_id="job-id", generation="generation-id", worker_id="worker") is False
    assert connection.rollbacks == 1
    assert connection.commits == 0
    assert len(connection.calls) == 2


def test_processing_stage_fence_rolls_back_video_update(monkeypatch) -> None:
    connection = FakeConnection(rowcounts=[1, 0])
    repository = MediaRepository()
    monkeypatch.setattr(repository, "_connect", lambda: _connection_context(connection))

    from media_worker.packager import MediaProbe

    assert repository.mark_processing(
        video_id="video-id", job_id="job-id", generation="generation-id",
        probe=MediaProbe(duration_seconds=1.0, width=640, height=360, video_codec="h264", audio_codec="aac", source_bitrate=1000, has_audio=True),
    ) is False
    assert connection.rollbacks == 1
    assert connection.commits == 0


def test_success_video_fence_rolls_back_terminal_job_and_artifacts(monkeypatch) -> None:
    connection = FakeConnection(rowcounts=[1, 1, 1, 0])
    repository = MediaRepository()
    monkeypatch.setattr(repository, "_connect", lambda: _connection_context(connection))

    result = repository.mark_succeeded(
        video_id="video-id", job_id="job-id", generation="generation-id",
        master_key="processed/video-id/attempts/generation-id/hls/master.m3u8",
        thumbnail_key="processed/video-id/attempts/generation-id/hls/thumbnail.jpg",
        generated_thumbnail_keys=["processed/video-id/attempts/generation-id/hls/thumbnail.jpg"],
        renditions=[_rendition("generation-id")],
        uploaded_assets=_complete_assets("generation-id"),
    )
    assert result.applied is False
    assert connection.rollbacks == 1
    assert connection.commits == 0


def test_failure_video_fence_rolls_back_terminal_job(monkeypatch) -> None:
    connection = FakeConnection(rowcounts=[1, 0])
    repository = MediaRepository()
    monkeypatch.setattr(repository, "_connect", lambda: _connection_context(connection))

    from media_worker.repository import ProcessingFailure

    assert repository.mark_failed(
        video_id="video-id", job_id="job-id", generation="generation-id",
        failure=ProcessingFailure(code="BROKEN", message="bad"),
    ) is False
    assert connection.rollbacks == 1
    assert connection.commits == 0


def test_stale_success_is_ignored(monkeypatch) -> None:
    connection = FakeConnection(rowcounts=[0])
    repository = MediaRepository()
    monkeypatch.setattr(repository, "_connect", lambda: _connection_context(connection))

    result = repository.mark_succeeded(
        video_id="video-id",
        job_id="job-id",
        generation="generation-id",
        master_key="processed/video-id/attempts/generation-id/hls/master.m3u8",
        thumbnail_key="processed/video-id/attempts/generation-id/hls/thumbnail.jpg",
        generated_thumbnail_keys=["processed/video-id/attempts/generation-id/hls/thumbnail.jpg"],
        renditions=[_rendition("generation-id")],
        uploaded_assets=_complete_assets("generation-id"),
    )
    assert result.applied is False
    assert not any("insert into video_asset_inventory" in query for query, _ in connection.calls)


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

    result = repository.mark_succeeded(
        video_id="video-id",
        job_id="job-id",
        generation="generation-id",
        master_key="processed/video-id/attempts/generation-id/hls/master.m3u8",
        thumbnail_key="processed/video-id/attempts/generation-id/hls/thumbnail.jpg",
        generated_thumbnail_keys=["processed/video-id/attempts/generation-id/hls/thumbnail.jpg"],
        renditions=[_rendition("generation-id")],
        uploaded_assets=_complete_assets("generation-id"),
    )

    assert result.applied is True
    assert result.old_generation == "old-generation"
    assert any("set status = 'ready'" in query for query, _ in connection.calls)
    assert any("set status = 'succeeded'" in query for query, _ in connection.calls)
    inventory_query, inventory_params = next(
        (query, params) for query, params in connection.calls if "insert into video_asset_inventory" in query
    )
    assert "relative_path" in inventory_query
    assert isinstance(inventory_params, list)
    assert any(params[3:] == ("master.m3u8", "application/vnd.apple.mpegurl", 100, "a" * 64) for params in inventory_params)


def test_missing_master_returns_false_before_db_mutation(monkeypatch) -> None:
    connection = FakeConnection()
    repository = MediaRepository()
    monkeypatch.setattr(repository, "_connect", lambda: _connection_context(connection))

    result = repository.mark_succeeded(
        video_id="video-id",
        job_id="job-id",
        generation="generation-id",
        master_key="processed/video-id/attempts/generation-id/hls/master.m3u8",
        thumbnail_key="processed/video-id/attempts/generation-id/hls/thumbnail.jpg",
        generated_thumbnail_keys=["processed/video-id/attempts/generation-id/hls/thumbnail.jpg"],
        renditions=[_rendition("generation-id")],
        uploaded_assets=_complete_assets("generation-id", include_master=False),
    )

    assert result.applied is False
    assert connection.calls == []
    assert connection.commits == 0


def test_empty_rendition_returns_false_before_db_mutation(monkeypatch) -> None:
    connection = FakeConnection()
    repository = MediaRepository()
    monkeypatch.setattr(repository, "_connect", lambda: _connection_context(connection))

    result = repository.mark_succeeded(
        video_id="video-id",
        job_id="job-id",
        generation="generation-id",
        master_key="processed/video-id/attempts/generation-id/hls/master.m3u8",
        thumbnail_key="processed/video-id/attempts/generation-id/hls/thumbnail.jpg",
        generated_thumbnail_keys=["processed/video-id/attempts/generation-id/hls/thumbnail.jpg"],
        renditions=[_rendition("generation-id")],
        uploaded_assets=_complete_assets("generation-id", include_segment=False),
    )

    assert result.applied is False
    assert connection.calls == []
    assert connection.commits == 0


def test_duplicate_inventory_path_returns_false_before_db_mutation(monkeypatch) -> None:
    connection = FakeConnection()
    repository = MediaRepository()
    monkeypatch.setattr(repository, "_connect", lambda: _connection_context(connection))
    assets = _complete_assets("generation-id")
    assets.append(assets[0])

    result = repository.mark_succeeded(
        video_id="video-id",
        job_id="job-id",
        generation="generation-id",
        master_key="processed/video-id/attempts/generation-id/hls/master.m3u8",
        thumbnail_key="processed/video-id/attempts/generation-id/hls/thumbnail.jpg",
        generated_thumbnail_keys=["processed/video-id/attempts/generation-id/hls/thumbnail.jpg"],
        renditions=[_rendition("generation-id")],
        uploaded_assets=assets,
    )

    assert result.applied is False
    assert result.reason == "duplicate_relative_path"
    assert connection.calls == []


def test_deleted_video_fence_returns_false_without_terminal_mutation(monkeypatch) -> None:
    connection = FakeConnection(video_exists=False)
    repository = MediaRepository()
    monkeypatch.setattr(repository, "_connect", lambda: _connection_context(connection))

    result = repository.mark_succeeded(
        video_id="video-id",
        job_id="job-id",
        generation="generation-id",
        master_key="processed/video-id/attempts/generation-id/hls/master.m3u8",
        thumbnail_key="processed/video-id/attempts/generation-id/hls/thumbnail.jpg",
        generated_thumbnail_keys=["processed/video-id/attempts/generation-id/hls/thumbnail.jpg"],
        renditions=[_rendition("generation-id")],
        uploaded_assets=_complete_assets("generation-id"),
    )

    assert result.applied is False
    query, _ = connection.calls[0]
    assert "active_processing_generation = %s" in query
    assert "deleted_at is null" in query
    assert "deletion_status = 'complete'" in query
    assert not any("update video_processing_jobs" in query for query, _ in connection.calls)


def test_success_fences_include_generation_and_tombstone_predicates(monkeypatch) -> None:
    connection = FakeConnection()
    repository = MediaRepository()
    monkeypatch.setattr(repository, "_connect", lambda: _connection_context(connection))

    repository.mark_succeeded(
        video_id="video-id",
        job_id="job-id",
        generation="generation-id",
        master_key="processed/video-id/attempts/generation-id/hls/master.m3u8",
        thumbnail_key="processed/video-id/attempts/generation-id/hls/thumbnail.jpg",
        generated_thumbnail_keys=["processed/video-id/attempts/generation-id/hls/thumbnail.jpg"],
        renditions=[_rendition("generation-id")],
        uploaded_assets=_complete_assets("generation-id"),
    )

    job_query = next(query for query, _ in connection.calls if "update video_processing_jobs" in query)
    video_query = next(query for query, _ in connection.calls if "update videos set status = 'ready'" in query)
    for query in (job_query, video_query):
        assert "video_id" in query
        assert "generation" in query
        assert "active_processing_generation" in query
        assert "deleted_at is null" in query
        assert "deletion_status = 'complete'" in query


def test_successful_publish_returns_prior_generation_for_post_commit_cleanup(monkeypatch) -> None:
    connection = FakeConnection()
    repository = MediaRepository()
    monkeypatch.setattr(repository, "_connect", lambda: _connection_context(connection))

    result = repository.mark_succeeded(
        video_id="video-id",
        job_id="job-id",
        generation="generation-id",
        master_key="processed/video-id/attempts/generation-id/hls/master.m3u8",
        thumbnail_key="processed/video-id/attempts/generation-id/hls/thumbnail.jpg",
        generated_thumbnail_keys=["processed/video-id/attempts/generation-id/hls/thumbnail.jpg"],
        renditions=[_rendition("generation-id")],
        uploaded_assets=_complete_assets("generation-id"),
    )

    assert result == PublicationResult(applied=True, old_generation="old-generation")
    assert connection.commits == 1


def test_custom_thumbnail_remains_selected_during_generated_replacement(monkeypatch) -> None:
    connection = FakeConnection(custom_thumbnail_exists=True)
    repository = MediaRepository()
    monkeypatch.setattr(repository, "_connect", lambda: _connection_context(connection))

    result = repository.mark_succeeded(
        video_id="video-id",
        job_id="job-id",
        generation="generation-id",
        master_key="processed/video-id/attempts/generation-id/hls/master.m3u8",
        thumbnail_key="processed/video-id/attempts/generation-id/hls/thumbnail.jpg",
        generated_thumbnail_keys=["processed/video-id/attempts/generation-id/hls/thumbnail.jpg"],
        renditions=[_rendition("generation-id")],
        uploaded_assets=_complete_assets("generation-id"),
    )

    assert result.applied is True
    thumbnail_query, thumbnail_params = next(
        (query, params) for query, params in connection.calls if "insert into video_thumbnails" in query
    )
    assert "source" in thumbnail_query
    assert isinstance(thumbnail_params, list)
    assert all(params[4] is False for params in thumbnail_params)
    video_params = next(params for query, params in connection.calls if "update videos set status = 'ready'" in query)
    assert isinstance(video_params, tuple)
    assert video_params[1] is None


def test_celery_cleans_prior_attempt_after_publish_without_touching_new_or_legacy(monkeypatch, tmp_path) -> None:
    from media_worker import celery_app as celery_module
    from media_worker.packager import MediaProbe

    class FakeRepository:
        def __init__(self) -> None:
            self.uploaded_assets: list[UploadedHlsAsset] = []

        def mark_started(self, **kwargs) -> bool:
            return True

        def mark_stage(self, **kwargs) -> bool:
            return True

        def mark_processing(self, **kwargs) -> bool:
            return True

        def mark_succeeded(self, *, uploaded_assets, **kwargs) -> PublicationResult:
            self.uploaded_assets = uploaded_assets
            return PublicationResult(applied=True, old_generation="old-generation")

    class FakeStorage:
        def __init__(self) -> None:
            self.objects = {
                "processed/video-id/attempts/old-generation/hls/master.m3u8",
                "processed/video-id/attempts/generation-id/hls/master.m3u8",
                "processed/video-id/hls/master.m3u8",
            }
            self.delete_calls: list[tuple[str, str]] = []

        def download_original(self, key: str, destination) -> None:
            destination.write_bytes(b"source")

        def upload_hls_tree(self, **kwargs) -> list[UploadedHlsAsset]:
            return _complete_assets("generation-id")

        def delete_hls_tree(self, *, video_id: str, generation: str) -> int:
            self.delete_calls.append((video_id, generation))
            prefix = f"processed/{video_id}/attempts/{generation}/hls/"
            before = len(self.objects)
            self.objects = {key for key in self.objects if not key.startswith(prefix)}
            return before - len(self.objects)

    repository = FakeRepository()
    storage = FakeStorage()
    monkeypatch.setattr(celery_module, "MediaRepository", lambda: repository)
    monkeypatch.setattr(celery_module, "ObjectStorage", lambda: storage)
    monkeypatch.setattr(
        celery_module,
        "probe_media",
        lambda source: MediaProbe(
            duration_seconds=1.0,
            width=640,
            height=360,
            video_codec="h264",
            audio_codec="aac",
            source_bitrate=1000,
            has_audio=True,
        ),
    )

    def fake_package_to_hls(*, generation: str, output_root, **kwargs) -> PackageResult:
        hls_root = output_root / "hls"
        hls_root.mkdir(parents=True)
        return PackageResult(
            generation=generation,
            hls_root=hls_root,
            master_storage_key=f"processed/video-id/attempts/{generation}/hls/master.m3u8",
            thumbnail_storage_key=f"processed/video-id/attempts/{generation}/hls/thumbnail.jpg",
            generated_thumbnail_storage_keys=[f"processed/video-id/attempts/{generation}/hls/thumbnail.jpg"],
            renditions=[_rendition(generation)],
        )

    monkeypatch.setattr(celery_module, "package_to_hls", fake_package_to_hls)

    result = celery_module.process_video.run("video-id", "job-id", "generation-id", "originals/video.mp4")

    assert result["status"] == "ready"
    assert repository.uploaded_assets == _complete_assets("generation-id")
    assert storage.delete_calls == [("video-id", "old-generation")]
    assert storage.objects == {
        "processed/video-id/attempts/generation-id/hls/master.m3u8",
        "processed/video-id/hls/master.m3u8",
    }


def _complete_assets(
    generation: str,
    *,
    include_master: bool = True,
    include_segment: bool = True,
) -> list[UploadedHlsAsset]:
    prefix = f"processed/video-id/attempts/{generation}/hls/"
    assets: list[UploadedHlsAsset] = []
    if include_master:
        assets.append(_asset(prefix, "master.m3u8", "application/vnd.apple.mpegurl", 100, "a" * 64))
    assets.append(_asset(prefix, "thumbnail.jpg", "image/jpeg", 101, "b" * 64))
    assets.append(_asset(prefix, "360p/playlist.m3u8", "application/vnd.apple.mpegurl", 102, "c" * 64))
    if include_segment:
        assets.append(_asset(prefix, "360p/segment_000.ts", "video/mp2t", 103, "d" * 64))
    return assets


def _asset(prefix: str, relative_path: str, content_type: str, size_bytes: int, sha256: str) -> UploadedHlsAsset:
    return UploadedHlsAsset(
        storage_key=f"{prefix}{relative_path}",
        relative_path=relative_path,
        content_type=content_type,
        size_bytes=size_bytes,
        sha256=sha256,
    )


def _rendition(generation: str) -> PackagedRendition:
    return PackagedRendition(
        label="360p",
        width=640,
        height=360,
        target_bitrate=800000,
        video_codec="h264",
        segment_count=1,
        output_size_bytes=205,
        playlist_storage_key=f"processed/video-id/attempts/{generation}/hls/360p/playlist.m3u8",
    )


@contextmanager
def _connection_context(connection: FakeConnection):
    yield connection
