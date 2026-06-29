# 290626-E-api-hls-playback-proxy

Sector: E delivery, playback, and CDN pathing
Agent: Codex
Date: 29-06-2026
Branch/Commit: main / pending local commit

## What changed
- Replaced the placeholder HLS route with an authenticated FastAPI proxy for generated HLS assets.
- Added processed-HLS MinIO storage reads from `MINIO_BUCKET_PROCESSED`.
- Added route validation for master playlist, thumbnail, rendition playlists, and segment files.
- Documented cache headers and the future CDN migration path.

## Decisions / ADR notes
- Decision: Keep browser playback on API-owned HLS URLs and read processed assets from the processed MinIO bucket.
- Reason: Matches the MVP private-playback contract and Sector D's worker output/upload target.
- Alternatives considered: Direct MinIO/presigned playback remains deferred until private playback can stay protected.

## Validation
- `pytest` from `apps/api` (24 passed)
- `npm --workspace apps/web run lint`
- `npm --workspace apps/web test`
- `npm --workspace apps/web run build`
- `make lint`
- `make test`
- `make smoke`
- Live API smoke with temporary local dev auth: created/uploaded `fixtures/media/sample-2s.mp4`, worker marked video ready, fetched playback metadata, master playlist, rendition playlist, `segment_000.ts`, and thumbnail through API HLS URLs.

## Files touched
- apps/api/app/api/videos.py
- apps/api/app/services/storage.py
- apps/api/app/api/deps.py
- apps/api/app/core/config.py
- apps/api/tests/test_video_api.py
- apps/api/tests/test_storage.py
- docs/delivery-playback-cdn.md

## Handoff / risks
- The API now enforces readiness and owner/public/unlisted access before any HLS object read.
- Segment responses use long immutable cache headers; future reprocessing should version processed prefixes or purge CDN cache.
- Browser playback still depends on Clerk cookies/tokens reaching the same-origin Next.js proxy for private videos.
