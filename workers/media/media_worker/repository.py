from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row

from media_worker import config
from media_worker.packager import MediaProbe, PackagedRendition


@dataclass(frozen=True)
class ProcessingFailure:
    code: str
    message: str


class MediaRepository:
    def __init__(self) -> None:
        self._database_url = config.database_url()

    def mark_started(self, *, video_id: str, job_id: str, generation: str, worker_id: str) -> bool:
        with self._connect() as conn:
            with conn.transaction():
                claimed = conn.execute(
                    """
                    update video_processing_jobs as job
                    set status = 'running',
                        stage = 'downloading',
                        attempt_count = job.attempt_count + 1,
                        worker_id = %s,
                        started_at = now(),
                        error_code = null,
                        error_message = null
                    from videos
                    where job.id = %s
                      and job.video_id = %s
                      and job.generation = %s
                      and job.status = 'queued'
                      and videos.id = job.video_id
                      and videos.status = 'queued'
                      and videos.active_processing_generation = job.generation
                    returning job.id
                    """,
                    (worker_id, job_id, video_id, generation),
                ).fetchone()
                if claimed is None:
                    return False
                conn.execute(
                    """
                    update videos
                    set status = 'probing',
                        failure_code = null,
                        failure_message = null,
                        updated_at = now()
                    where id = %s
                      and active_processing_generation = %s
                      and status = 'queued'
                    """,
                    (video_id, generation),
                )
        return True

    def mark_processing(self, *, video_id: str, job_id: str, generation: str, probe: MediaProbe) -> bool:
        with self._connect() as conn:
            updated = conn.execute(
                """
                update videos
                set status = 'processing',
                    duration_seconds = %s,
                    width = %s,
                    height = %s,
                    video_codec = %s,
                    audio_codec = %s,
                    source_bitrate = %s,
                    updated_at = now()
                from video_processing_jobs as job
                where videos.id = %s
                  and job.id = %s
                  and job.video_id = videos.id
                  and job.generation = %s
                  and job.status = 'running'
                  and videos.active_processing_generation = job.generation
                """,
                (
                    Decimal(str(round(probe.duration_seconds, 3))) if probe.duration_seconds is not None else None,
                    probe.width,
                    probe.height,
                    probe.video_codec,
                    probe.audio_codec,
                    probe.source_bitrate,
                    video_id,
                    job_id,
                    generation,
                ),
            )
            if updated.rowcount != 1:
                return False
            stage = conn.execute(
                "update video_processing_jobs set stage = 'packaging' where id = %s and video_id = %s and generation = %s and status = 'running'",
                (job_id, video_id, generation),
            )
            return stage.rowcount == 1

    def mark_stage(self, *, video_id: str, job_id: str, generation: str, stage: str) -> bool:
        with self._connect() as conn:
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
    ) -> bool:
        with self._connect() as conn:
            with conn.transaction():
                claimed = conn.execute(
                    """
                    update video_processing_jobs as job
                    set status = 'succeeded', stage = 'complete', finished_at = now(), error_code = null, error_message = null
                    where job.id = %s and job.video_id = %s and job.generation = %s and job.status = 'running'
                      and exists (select 1 from videos where videos.id = job.video_id and videos.active_processing_generation = job.generation)
                    """,
                    (job_id, video_id, generation),
                )
                if claimed.rowcount != 1:
                    return False
                custom_thumbnail_exists = conn.execute(
                    "select exists(select 1 from video_thumbnails where video_id = %s and source = 'custom' and selected) as custom_thumbnail_exists",
                    (video_id,),
                ).fetchone()["custom_thumbnail_exists"]
                conn.execute("delete from video_renditions where video_id = %s", (video_id,))
                for rendition in renditions:
                    conn.execute(
                        """
                        insert into video_renditions
                            (id, video_id, label, width, height, target_bitrate, video_codec, segment_count, output_size_bytes, playlist_storage_key, status, created_at)
                        values
                            (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'ready', now())
                        """,
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
                        ),
                    )
                conn.execute("delete from video_thumbnails where video_id = %s and source = 'generated'", (video_id,))
                for index, storage_key in enumerate(generated_thumbnail_keys):
                    conn.execute(
                        """
                        insert into video_thumbnails
                            (id, video_id, storage_key, source, content_type, width, height, selected, created_at)
                        values (%s, %s, %s, 'generated', 'image/jpeg', 640, 360, %s, now())
                        """,
                        (str(uuid4()), video_id, storage_key, index == 0 and not custom_thumbnail_exists),
                    )
                updated = conn.execute(
                    """
                    update videos
                    set status = 'ready',
                        hls_master_storage_key = %s,
                        thumbnail_storage_key = coalesce(%s, thumbnail_storage_key),
                        failure_code = null,
                        failure_message = null,
                        updated_at = now()
                    where id = %s and active_processing_generation = %s
                    """,
                    (master_key, thumbnail_key if not custom_thumbnail_exists else None, video_id, generation),
                )
                if updated.rowcount != 1:
                    return False
        return True

    def mark_failed(self, *, video_id: str, job_id: str, generation: str, failure: ProcessingFailure) -> bool:
        safe_message = failure.message[:500]
        with self._connect() as conn:
            with conn.transaction():
                claimed = conn.execute(
                    """
                    update video_processing_jobs as job
                    set status = 'failed', stage = 'failed', finished_at = now(), error_code = %s, error_message = %s
                    where job.id = %s and job.video_id = %s and job.generation = %s and job.status = 'running'
                      and exists (select 1 from videos where videos.id = job.video_id and videos.active_processing_generation = job.generation)
                    """,
                    (failure.code, safe_message, job_id, video_id, generation),
                )
                if claimed.rowcount != 1:
                    return False
                updated = conn.execute(
                    """
                    update videos
                    set status = 'failed',
                        failure_code = %s,
                        failure_message = %s,
                        updated_at = now()
                    where id = %s and active_processing_generation = %s
                    """,
                    (failure.code, safe_message, video_id, generation),
                )
                return updated.rowcount == 1

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(self._database_url, row_factory=dict_row)
