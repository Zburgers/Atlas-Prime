# 150726-E-signed-playback-mode

Sector: E - Media Processing and Delivery
Agent: Codex
Date: 15-07-2026
Branch/Commit: docs/fullplatform-rollout

## What changed
- Added opt-in `signed-redirect` playback responses that mint a short-lived, versioned master manifest URL after existing playback authorization succeeds.
- Preserved `/hls/` proxy delivery as the default mode.

## Decisions / ADR notes
- Decision: Bind minted tokens to the Atlas user UUID when a viewer is authenticated; keep public playback tokens viewerless.
- Reason: The token remains a short-lived bearer credential while retaining useful audit and revocation context.

## Validation
- `docker compose run --rm --build api pytest tests/test_video_api.py tests/test_playback_delivery.py -q` (29 passed)
- `docker compose run --rm api python -m compileall -q app`

## Files touched
- apps/api/app/api/videos.py
- apps/api/tests/test_video_api.py

## Handoff / risks
- Signed mode requires `ATLAS_PLAYBACK_DELIVERY_MODE=signed-redirect`, a 32-character `ATLAS_PLAYBACK_TOKEN_SECRET`, and a browser-reachable CORS-enabled `MINIO_PUBLIC_ENDPOINT`.
- The HLS player already uses `master_playlist_url`; frontend browser validation should be performed with signed mode enabled and a real public object endpoint.
