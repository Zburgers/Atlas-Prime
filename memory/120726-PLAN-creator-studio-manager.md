# 120726-PLAN-creator-studio-manager

Sector: Cross-sector platform rollout
Agent: Codex
Date: 12-07-2026
Branch/Commit: docs/fullplatform-rollout

## What changed
- Implemented Phase 1 Issue 6 with owner-only Creator Studio video management.
- Added `/studio/videos` list, metadata/privacy edit, and failed-video retry endpoints.
- Added Studio navigation, landing page, and video manager UI with filters, inline edits, and retry action.
- Updated the rollout plan so Issue 7 Comments V1 is the next implementation unit.

## Decisions / ADR notes
- Decision: Studio retry only requeues `failed` videos that still have an original storage key.
- Reason: Retrying without an uploaded original would enqueue an impossible worker job.
- Alternatives considered: Retrying draft/upload validation failures from Studio was deferred to the upload flow.

## Validation
- `docker compose run --rm --build api pytest tests/test_studio.py -q` failed red before routes existed, then passed.
- `docker compose run --rm --build web-test npm --workspace apps/web run lint` passed.
- `make test` passed: 47 API tests, 2 worker tests, 1 web test.
- `make lint` passed.
- `make smoke` passed against the live Compose stack.
- `curl -fsS http://127.0.0.1:3001/studio` rendered.
- `curl -fsS http://127.0.0.1:3001/studio/videos` rendered.
- `curl -fsS -H 'X-Atlas-Dev-Clerk-User-Id: live-studio-probe' http://127.0.0.1:8000/studio/videos?page_size=1` returned an owner-scoped empty list.

## Files touched
- `apps/api/app/api/studio.py`
- `apps/api/app/services/studio.py`
- `apps/api/app/schemas/studio.py`
- `apps/api/app/main.py`
- `apps/api/tests/test_studio.py`
- `apps/web/app/components/app-header.tsx`
- `apps/web/app/components/video-api.ts`
- `apps/web/app/studio/page.tsx`
- `apps/web/app/studio/videos/page.tsx`
- `apps/web/app/studio/videos/studio-video-manager.tsx`
- `apps/web/app/globals.css`
- `docs/plans/02-fullplatform-vision.md`

## Handoff / risks
- Next rollout issue is Phase 1 Issue 7: Comments V1.
- Studio retry creates a new queued processing job but does not expose Celery task IDs in the response.
- The Studio list is owner-scoped and intentionally separate from public discovery surfaces.
