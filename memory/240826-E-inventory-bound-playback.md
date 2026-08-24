# 240826-E-inventory-bound-playback

Sector: E
Agent: Luna
Date: 24-08-2026
Branch/Commit: docs/fullplatform-rollout / a417095 (working tree uncommitted)

## What changed
- API playback and signed delivery now eager-load `Video.asset_inventory` and authorize master playlists, rendition playlists, segments, and generated `thumbnail.jpg` only from the published generation inventory.
- Published generation is derived only from the strict `processed/{video_id}/attempts/{generation}/hls/master.m3u8` key; legacy and stale-generation keys fail closed without a storage read.
- Test ready fixtures now create attempt-scoped publication keys and typed inventory rows; smoke requests a valid but uninventoried segment and expects 404.

## Decisions / ADR notes
- Decision: keep route MIME, cache, playlist rewriting, redirect, authorization, and token behavior unchanged while making inventory membership the storage authorization boundary.
- Reason: a correctly patterned or existing object must not be playable unless it belongs to the currently published generation.
- Alternatives considered: no legacy-prefix fallback, direct storage existence checks, new URL formats, or frontend changes.

## Validation
- `docker compose run --rm --build api pytest tests/test_playback_delivery.py tests/test_video_api.py -q` -> PASS, 39 passed.
- `docker compose run --rm --build api pytest -q` -> PASS, 123 passed.
- `docker compose run --rm api python -m compileall -q app tests` -> PASS.
- `ruff check apps/api/app/api/videos.py apps/api/app/services/videos.py apps/api/tests/test_video_api.py apps/api/tests/test_playback_delivery.py` -> PASS; container image has no ruff executable.
- `sh -n scripts/smoke-devex.sh` and `git diff --check` -> PASS.

## Files touched
- `apps/api/app/api/videos.py`
- `apps/api/app/services/videos.py`
- `apps/api/tests/test_playback_delivery.py`
- `apps/api/tests/test_video_api.py`
- `scripts/smoke-devex.sh`

## Handoff / risks
- Task 3.5 still owns tombstone/deletion reconciliation; this task does not alter custom thumbnail delivery or deletion workflows.
- Task 3.4 must bind API serving to the active inventory, while full-stack smoke remains deferred until Tasks 3.4 and 3.5 are complete.
- Merge, deployment, authenticated browser qualification, and production readiness are not claimed.
