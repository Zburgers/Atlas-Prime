# 150726-E-signed-playlist-rewriting

Sector: E - Media Processing and Delivery
Agent: Codex
Date: 15-07-2026
Branch/Commit: docs/fullplatform-rollout

## What changed
- Added signed delivery of HLS manifests through FastAPI.
- Rewrote relative rendition and segment URIs in each manifest with the existing short-lived playback token.

## Decisions / ADR notes
- Decision: Keep playlists API-served and redirect only media objects to MinIO.
- Reason: HLS clients need the token on every nested request, while segment traffic remains off the API data plane.

## Validation
- `docker compose run --rm --build api pytest tests/test_video_api.py -q` (27 passed)
- `docker compose run --rm api python -m compileall -q app`

## Files touched
- apps/api/app/api/videos.py
- apps/api/tests/test_video_api.py

## Handoff / risks
- The playback endpoint still returns the proxy URL. The next slice must mint a token only after normal access checks and return the signed master URL only when `ATLAS_PLAYBACK_DELIVERY_MODE=signed-redirect`.
- Current worker output contains relative URI lines; support for HLS URI attributes such as `EXT-X-MAP` would need explicit rewriting if fMP4 packaging is introduced.
