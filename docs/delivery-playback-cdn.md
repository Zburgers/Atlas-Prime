# Delivery, Playback, and CDN Notes

Sector E keeps playback API-owned for the MVP. Browsers receive URLs such as
`/videos/{video_id}/hls/master.m3u8` from `GET /videos/{video_id}/playback`;
the API validates readiness and viewer access, eager-loads the committed asset
inventory, and reads only an inventoried object from `MINIO_BUCKET_PROCESSED`
under `processed/{video_id}/attempts/{generation}/hls/{relative_path}`.

## Published asset binding

- The worker writes only immutable attempt prefixes:
  `processed/{video_id}/attempts/{generation}/hls/{relative_path}`. The legacy
  `processed/{video_id}/hls/` prefix is neither a current output location nor a
  valid playback source.
- The API derives the published generation from the strict current
  `videos.hls_master_storage_key` ending in
  `attempts/{generation}/hls/master.m3u8`. It does not use
  `active_processing_generation`, because a retry may be active while an older
  generation remains published.
- A syntactically valid master, rendition playlist, segment, or generated
  `thumbnail.jpg` must have a matching `video_asset_inventory.relative_path`
  for that published generation. The API constructs the storage key from the
  validated inventory row; object existence or filename shape alone is not
  authorization. Uninventoried, stale-generation, and legacy paths return
  404 before a storage read. Traversal, absolute, empty-component, unsupported,
  and malformed paths remain 400.
- Master and rendition playlists stay API-proxied. Signed playlist rewriting
  preserves API-owned relative URIs, while signed segment delivery remains a
  307 redirect. Authorization and privacy checks are unchanged.

## Cache Headers

- Playlists (`master.m3u8`, rendition `playlist.m3u8`): `private, no-cache`
- Segments (`segment_*.ts`, `segment_*.m4s`, `segment_*.mp4`): `private, max-age=31536000, immutable`
- Thumbnail (`thumbnail.jpg`): `private, max-age=300`

The segment header assumes attempt-scoped HLS outputs are immutable once a
video is ready. A future publication design must retain generation versioning
or purge any CDN cache before changing delivery behavior.

## CDN Migration Path

The CDN should sit in front of the API HLS route, not MinIO directly, until
private playback is protected by an equivalent token or signed URL design.
A future CDN layer can cache segment responses aggressively while keeping
playlist responses revalidated. The worker output layout does not need to
change for that migration.
