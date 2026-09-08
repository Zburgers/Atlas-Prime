# 050826-A-contract-redacted-callers

Sector: A — Product and Web App Shell
Agent: plan1_task13
Date: 05-08-2026
Branch/Commit: docs/fullplatform-rollout (uncommitted handoff)

## What changed
- Removed storage-key, rendition-playlist-key, upload storage-key, and Celery task ID fields from normal web API types.
- Added separate admin debug types for protected storage-backed video and rendition fields.
- Added smoke assertions for redacted normal contracts and admin debug type usage.
- Added API playback assertion that normal rendition metadata omits `playlist_storage_key`.

## Decisions / ADR notes
- Decision: Keep API-owned URLs and domain state in product contracts; expose storage internals only through protected admin debug responses.
- Reason: Prevent normal clients from depending on internal storage or queue implementation details.

## Validation
- `docker compose run --rm --build web-test npm --workspace apps/web test` — 3 passed.
- `docker compose run --rm --build web-test npm --workspace apps/web run build` — production build passed.
- `docker compose run --rm --build api pytest tests/test_video_api.py tests/test_playback_delivery.py -q` — 33 passed.
- `git diff --check` — passed.

## Files touched
- `apps/web/app/components/video-api.ts`
- `apps/web/app/admin/admin-dashboard.tsx`
- `apps/web/tests/smoke.test.js`
- `apps/api/tests/test_video_api.py`

## Handoff / risks
- Parent agent should review and commit these scoped changes with the Plan 1 evidence.
- No API implementation changes were made; Task 1.2 schemas remain the source of truth.
- Do not re-add redacted fields to normal product types; use an explicit protected debug type if an operator view needs them.
