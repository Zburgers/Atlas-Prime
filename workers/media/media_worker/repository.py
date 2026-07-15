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

    def mark_started(self, *, video_id: str, job_id: str, worker_id: str) -> None:
        with self._connect() as conn:
            with conn.transaction():
                conn.execute(
                    """
                    update video_processing_jobs
                    set status = 'running',
                        attempt_count = attempt_count + 1,
                        worker_id = %s,
                        started_at = now(),
                        error_code = null,
                        error_message = null
                    where id = %s and video_id = %s
                    """,
                    (worker_id, job_id, video_id),
                )
                conn.execute(
                    """
                    update videos
                    set status = 'probing',
                        failure_code = null,
                        failure_message = null,
                        updated_at = now()
                    where id = %s
                    """,
                    (video_id,),
                )

    def mark_processing(self, *, video_id: str, probe: MediaProbe) -> None:
        with self._connect() as conn:
            conn.execute(
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
                where id = %s
                """,
                (
                    Decimal(str(round(probe.duration_seconds, 3))) if probe.duration_seconds is not None else None,
                    probe.width,
                    probe.height,
                    probe.video_codec,
                    probe.audio_codec,
                    probe.source_bitrate,
                    video_id,
                ),
            )

    def mark_succeeded(
        self,
        *,
        video_id: str,
        job_id: str,
        master_key: str,
        thumbnail_key: str,
        generated_thumbnail_keys: list[str],
        renditions: list[PackagedRendition],
    ) -> None:
        with self._connect() as conn:
            with conn.transaction():
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
                conn.execute(
                    """
                    update videos
                    set status = 'ready',
                        hls_master_storage_key = %s,
                        thumbnail_storage_key = coalesce(%s, thumbnail_storage_key),
                        failure_code = null,
                        failure_message = null,
                        updated_at = now()
                    where id = %s
                    """,
                    (master_key, thumbnail_key if not custom_thumbnail_exists else None, video_id),
                )
                conn.execute(
                    """
                    update video_processing_jobs
                    set status = 'succeeded',
                        finished_at = now(),
                        error_code = null,
                        error_message = null
                    where id = %s and video_id = %s
                    """,
                    (job_id, video_id),
                )

    def mark_failed(self, *, video_id: str, job_id: str, failure: ProcessingFailure) -> None:
        safe_message = failure.message[:500]
        with self._connect() as conn:
            with conn.transaction():
                conn.execute(
                    """
                    update videos
                    set status = 'failed',
                        failure_code = %s,
                        failure_message = %s,
                        updated_at = now()
                    where id = %s
                    """,
                    (failure.code, safe_message, video_id),
                )
                conn.execute(
                    """
                    update video_processing_jobs
                    set status = 'failed',
                        finished_at = now(),
                        error_code = %s,
                        error_message = %s
                    where id = %s and video_id = %s
                    """,
                    (failure.code, safe_message, job_id, video_id),
                )

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(self._database_url, row_factory=dict_row)
