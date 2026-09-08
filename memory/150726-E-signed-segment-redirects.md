# 150726-E-signed-segment-redirects

Sector: E - Media Processing and Delivery
Agent: Codex
Date: 15-07-2026
Branch/Commit: docs/fullplatform-rollout

## What changed
- Added a token-validated delivery route that redirects HLS segment requests to MinIO presigned URLs without proxying segment bytes through FastAPI.
- Presigned URLs now use the configured browser-reachable `MINIO_PUBLIC_ENDPOINT`; signed delivery rejects requests when that endpoint is absent.

## Decisions / ADR notes
- Decision: Keep signed asset delivery bearer-token based and load only ready, non-removed videos after token validation.
- Reason: Playback authorization occurs when the API mints the short-lived, versioned token, while direct segment delivery avoids API data-plane traffic.

## Validation
- `docker compose run --rm --build api pytest tests/test_video_api.py tests/test_storage.py -q` (29 passed)
- `docker compose run --rm api python -m compileall -q app`
- `ruff check app tests` not run: Ruff is not installed in the API image.

## Files touched
- apps/api/app/api/videos.py
- apps/api/app/services/videos.py
- apps/api/app/services/storage.py
- apps/api/tests/test_video_api.py
- apps/api/tests/test_storage.py

## Handoff / risks
- Playlist delivery is intentionally not switched yet: manifests must be rewritten to retain the token on nested playlist and segment requests before playback can opt into signed delivery.
- Deployments must configure a CORS-enabled `MINIO_PUBLIC_ENDPOINT` and `ATLAS_PLAYBACK_TOKEN_SECRET` before enabling signed redirect mode.
