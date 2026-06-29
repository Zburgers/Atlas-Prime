# Delivery, Playback, and CDN Notes

Sector E keeps playback API-owned for the MVP. Browsers receive URLs such as
`/videos/{video_id}/hls/master.m3u8` from `GET /videos/{video_id}/playback`;
the API validates readiness and viewer access, then reads the corresponding
object from `MINIO_BUCKET_PROCESSED` under `processed/{video_id}/hls/`.

## Cache Headers

- Playlists (`master.m3u8`, rendition `playlist.m3u8`): `private, no-cache`
- Segments (`segment_*.ts`, `segment_*.m4s`, `segment_*.mp4`): `private, max-age=31536000, immutable`
- Thumbnail (`thumbnail.jpg`): `private, max-age=300`

The segment header assumes processed HLS outputs are immutable once a video is
ready. If reprocessing overwrites the same key in a future phase, the worker
should version the processed prefix or purge any CDN cache before publishing the
new playlist.

## CDN Migration Path

The CDN should sit in front of the API HLS route, not MinIO directly, until
private playback is protected by an equivalent token or signed URL design.
A future CDN layer can cache segment responses aggressively while keeping
playlist responses revalidated. The worker output layout does not need to
change for that migration.
