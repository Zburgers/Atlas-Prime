from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import PurePosixPath
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row

from media_worker import config
from media_worker.packager import MediaProbe, PackagedRendition
from media_worker.storage import UploadedHlsAsset


@dataclass(frozen=True)
class ProcessingFailure:
    code: str
    message: str


@dataclass(frozen=True)
class PublicationResult:
    applied: bool
    old_generation: str | None = None
    reason: str | None = None

    def __bool__(self) -> bool:
        return self.applied


class _FenceLost(Exception):
    """Internal sentinel used to roll back a partially-applied fenced update."""


class MediaRepository:
    def __init__(self) -> None:
        self._database_url = config.database_url()

    def mark_started(self, *, video_id: str, job_id: str, generation: str, worker_id: str) -> bool:
        try:
            with self._connect() as conn:
                with conn.transaction():
                    claimed = conn.execute(
                        """update video_processing_jobs as job set status = 'running', stage = 'downloading',
                        attempt_count = job.attempt_count + 1, worker_id = %s, started_at = now(),
                        error_code = null, error_message = null from videos
                        where job.id = %s and job.video_id = %s and job.generation = %s and job.status = 'queued'
                          and videos.id = job.video_id and videos.status = 'queued'
                          and videos.active_processing_generation = job.generation returning job.id""",
                        (worker_id, job_id, video_id, generation),
                    ).fetchone()
                    if claimed is None:
                        return False
                    updated = conn.execute(
                        """update videos set status = 'probing', failure_code = null,
                        failure_message = null, updated_at = now()
                        where id = %s and active_processing_generation = %s and status = 'queued'
                          and exists (select 1 from video_processing_jobs where id = %s and video_id = videos.id and generation = %s and status = 'running')""",
                        (video_id, generation, job_id, generation),
                    )
                    if updated.rowcount != 1:
                        raise _FenceLost
            return True
        except _FenceLost:
            return False

    def mark_processing(self, *, video_id: str, job_id: str, generation: str, probe: MediaProbe) -> bool:
        try:
            with self._connect() as conn:
                with conn.transaction():
                    updated = conn.execute(
                        """
                        update videos
                        set status = 'processing', duration_seconds = %s, width = %s, height = %s,
                            video_codec = %s, audio_codec = %s, source_bitrate = %s, updated_at = now()
                        from video_processing_jobs as job
                        where videos.id = %s and job.id = %s and job.video_id = videos.id
                          and job.generation = %s and job.status = 'running'
                          and videos.active_processing_generation = job.generation
                        """,
                        (
                            Decimal(str(round(probe.duration_seconds, 3))) if probe.duration_seconds is not None else None,
                            probe.width, probe.height, probe.video_codec, probe.audio_codec,
                            probe.source_bitrate, video_id, job_id, generation,
                        ),
                    )
                    if updated.rowcount != 1:
                        raise _FenceLost
                    stage = conn.execute(
                        "update video_processing_jobs set stage = 'packaging' where id = %s and video_id = %s and generation = %s and status = 'running' and exists (select 1 from videos where videos.id = video_processing_jobs.video_id and videos.active_processing_generation = video_processing_jobs.generation)",
                        (job_id, video_id, generation),
                    )
                    if stage.rowcount != 1:
                        raise _FenceLost
            return True
        except _FenceLost:
            return False

    def mark_stage(self, *, video_id: str, job_id: str, generation: str, stage: str) -> bool:
        with self._connect() as conn:
            with conn.transaction():
                updated = conn.execute(
                    "update video_processing_jobs set stage = %s where id = %s and video_id = %s and generation = %s and status = 'running' and exists (select 1 from videos where videos.id = video_processing_jobs.video_id and videos.active_processing_generation = video_processing_jobs.generation)",
                    (stage, job_id, video_id, generation),
                )
                return updated.rowcount == 1

    def mark_succeeded(
        self,
        *,
        video_id: str,
        job_id: str,
        generation: str,
        master_key: str,
        thumbnail_key: str,
        generated_thumbnail_keys: list[str],
        renditions: list[PackagedRendition],
        uploaded_assets: list[UploadedHlsAsset],
    ) -> PublicationResult:
        manifest_error = _validate_manifest(
            video_id=video_id,
            generation=generation,
            master_key=master_key,
            thumbnail_key=thumbnail_key,
            generated_thumbnail_keys=generated_thumbnail_keys,
            renditions=renditions,
            uploaded_assets=uploaded_assets,
        )
        if manifest_error is not None:
            return PublicationResult(applied=False, reason=manifest_error)

        try:
            with self._connect() as conn:
                with conn.transaction():
                    video_row = conn.execute(
                        """
                        select hls_master_storage_key
                        from videos
                        where id = %s and active_processing_generation = %s
                          and deleted_at is null and deletion_status = 'complete'
                        for update
                        """,
                        (video_id, generation),
                    ).fetchone()
                    if video_row is None:
                        return PublicationResult(applied=False, reason="stale_or_deleted")
                    old_generation = _attempt_generation_from_master_key(
                        video_id=video_id,
                        storage_key=video_row["hls_master_storage_key"],
                    )

                    claimed = conn.execute(
                        """update video_processing_jobs as job
                        set status = 'succeeded', stage = 'complete', finished_at = now(), error_code = null, error_message = null
                        where job.id = %s and job.video_id = %s and job.generation = %s and job.status = 'running'
                          and exists (
                              select 1 from videos
                              where videos.id = job.video_id
                                and videos.active_processing_generation = job.generation
                                and videos.deleted_at is null and videos.deletion_status = 'complete'
                          )""",
                        (job_id, video_id, generation),
                    )
                    if claimed.rowcount != 1:
                        return PublicationResult(applied=False, reason="stale_or_deleted")

                    conn.executemany(
                        """
                        insert into video_asset_inventory
                            (id, video_id, generation, relative_path, content_type, size_bytes, sha256, created_at)
                        values (%s, %s, %s, %s, %s, %s, %s, now())
                        """,
                        [
                            (
                                str(uuid4()),
                                video_id,
                                generation,
                                asset.relative_path,
                                asset.content_type,
                                asset.size_bytes,
                                asset.sha256,
                            )
                            for asset in uploaded_assets
                        ],
                    )

                    custom_thumbnail_exists = conn.execute(
                        "select exists(select 1 from video_thumbnails where video_id = %s and source = 'custom' and selected) as custom_thumbnail_exists",
                        (video_id,),
                    ).fetchone()["custom_thumbnail_exists"]
                    conn.execute("delete from video_renditions where video_id = %s", (video_id,))
                    conn.executemany(
                        "insert into video_renditions (id, video_id, label, width, height, target_bitrate, video_codec, segment_count, output_size_bytes, playlist_storage_key, status, created_at) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'ready', now())",
                        [
                            (
                                str(uuid4()),
                                video_id,
                                rendition.label,
                                rendition.width,
                                rendition.height,
                                rendition.target_bitrate,
                                rendition.video_codec,
                                rendition.segment_count,
                                rendition.output_size_bytes,
                                rendition.playlist_storage_key,
                            )
                            for rendition in renditions
                        ],
                    )
                    conn.execute("delete from video_thumbnails where video_id = %s and source = 'generated'", (video_id,))
                    asset_by_key = {asset.storage_key: asset for asset in uploaded_assets}
                    conn.executemany(
                        "insert into video_thumbnails (id, video_id, storage_key, source, content_type, width, height, selected, created_at) values (%s, %s, %s, 'generated', %s, 640, 360, %s, now())",
                        [
                            (
                                str(uuid4()),
                                video_id,
                                storage_key,
                                asset_by_key[storage_key].content_type,
                                index == 0 and not custom_thumbnail_exists,
                            )
                            for index, storage_key in enumerate(generated_thumbnail_keys)
                        ],
                    )
                    updated = conn.execute(
                        """update videos set status = 'ready', hls_master_storage_key = %s,
                        thumbnail_storage_key = coalesce(%s, thumbnail_storage_key), failure_code = null,
                        failure_message = null, updated_at = now()
                        where id = %s and active_processing_generation = %s
                          and deleted_at is null and deletion_status = 'complete'
                          and exists (
                              select 1 from video_processing_jobs
                              where id = %s and video_id = videos.id and generation = %s and status = 'succeeded'
                          )""",
                        (master_key, thumbnail_key if not custom_thumbnail_exists else None, video_id, generation, job_id, generation),
                    )
                    if updated.rowcount != 1:
                        raise _FenceLost
            return PublicationResult(applied=True, old_generation=old_generation)
        except _FenceLost:
            return PublicationResult(applied=False, reason="stale_or_deleted")

    def mark_failed(self, *, video_id: str, job_id: str, generation: str, failure: ProcessingFailure) -> bool:
        safe_message = failure.message[:500]
        try:
            with self._connect() as conn:
                with conn.transaction():
                    claimed = conn.execute(
                        """update video_processing_jobs as job
                        set status = 'failed', stage = 'failed', finished_at = now(), error_code = %s, error_message = %s
                        where job.id = %s and job.video_id = %s and job.generation = %s and job.status = 'running'
                          and exists (select 1 from videos where videos.id = job.video_id and videos.active_processing_generation = job.generation)""",
                        (failure.code, safe_message, job_id, video_id, generation),
                    )
                    if claimed.rowcount != 1:
                        return False
                    updated = conn.execute(
                        """update videos set status = 'failed', failure_code = %s,
                        failure_message = %s, updated_at = now()
                        where id = %s and active_processing_generation = %s
                          and exists (select 1 from video_processing_jobs where id = %s and video_id = videos.id and generation = %s and status = 'failed')""",
                        (failure.code, safe_message, video_id, generation, job_id, generation),
                    )
                    if updated.rowcount != 1:
                        raise _FenceLost
            return True
        except _FenceLost:
            return False

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(self._database_url, row_factory=dict_row)


def _validate_manifest(
    *,
    video_id: str,
    generation: str,
    master_key: str,
    thumbnail_key: str,
    generated_thumbnail_keys: list[str],
    renditions: list[PackagedRendition],
    uploaded_assets: list[UploadedHlsAsset],
) -> str | None:
    if not uploaded_assets:
        return "empty_manifest"

    prefix = f"processed/{video_id}/attempts/{generation}/hls/"
    assets_by_relative: dict[str, UploadedHlsAsset] = {}
    assets_by_key: dict[str, UploadedHlsAsset] = {}
    for asset in uploaded_assets:
        relative_path = PurePosixPath(asset.relative_path)
        if (
            not asset.relative_path
            or relative_path.is_absolute()
            or not relative_path.parts
            or "." in relative_path.parts
            or ".." in relative_path.parts
            or "\\" in asset.relative_path
        ):
            return "unsafe_relative_path"
        expected_key = f"{prefix}{relative_path.as_posix()}"
        if asset.storage_key != expected_key:
            return "storage_key_mismatch"
        if asset.relative_path in assets_by_relative:
            return "duplicate_relative_path"
        if asset.storage_key in assets_by_key:
            return "duplicate_storage_key"
        if asset.size_bytes < 0 or not asset.content_type or not asset.sha256:
            return "invalid_asset_metadata"
        assets_by_relative[asset.relative_path] = asset
        assets_by_key[asset.storage_key] = asset

    if master_key != f"{prefix}master.m3u8" or "master.m3u8" not in assets_by_relative:
        return "missing_master"
    if thumbnail_key != f"{prefix}thumbnail.jpg" or "thumbnail.jpg" not in assets_by_relative:
        return "missing_thumbnail"
    if not generated_thumbnail_keys or thumbnail_key not in generated_thumbnail_keys:
        return "missing_generated_thumbnail"
    if len(generated_thumbnail_keys) != len(set(generated_thumbnail_keys)):
        return "duplicate_generated_thumbnail"
    if any(storage_key not in assets_by_key for storage_key in generated_thumbnail_keys):
        return "missing_generated_thumbnail_asset"
    if not renditions:
        return "empty_renditions"

    for rendition in renditions:
        playlist_path = f"{rendition.label}/playlist.m3u8"
        if rendition.playlist_storage_key != f"{prefix}{playlist_path}" or playlist_path not in assets_by_relative:
            return "missing_rendition_playlist"
        if not any(
            path.parent == PurePosixPath(rendition.label)
            and path.name.startswith("segment_")
            and path.suffix == ".ts"
            for path in (PurePosixPath(relative_path) for relative_path in assets_by_relative)
        ):
            return "empty_rendition"

    return None


def _attempt_generation_from_master_key(*, video_id: str, storage_key: str | None) -> str | None:
    if not storage_key:
        return None
    prefix = f"processed/{video_id}/attempts/"
    suffix = "/hls/master.m3u8"
    if not storage_key.startswith(prefix) or not storage_key.endswith(suffix):
        return None
    generation = storage_key[len(prefix) : -len(suffix)]
    if not generation or "/" in generation or "\\" in generation or generation in {".", ".."}:
        return None
    return generation
