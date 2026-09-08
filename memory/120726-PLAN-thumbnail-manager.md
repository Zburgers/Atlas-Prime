# 120726-PLAN-thumbnail-manager

Sector: Cross-sector platform rollout
Agent: Codex
Date: 12-07-2026
Branch/Commit: docs/fullplatform-rollout

## What changed
- Implemented Phase 1 Issue 10 with durable generated/custom thumbnail candidates and one selected candidate per video.
- Added owner-only Studio list, select, and custom PNG/JPEG upload endpoints plus a Studio thumbnail selector page.
- Moved public thumbnail delivery to the API-owned `/videos/{video_id}/thumbnail` URL.

## Decisions / ADR notes
- Decision: `videos.thumbnail_storage_key` remains the selected-thumbnail pointer while `video_thumbnails` records candidates.
- Reason: Existing playback/list contracts stay compatible while selection becomes durable and auditable.
- Alternatives considered: Exposing custom storage keys or serving MinIO directly were rejected.

## Validation
- `docker compose run --rm --build api pytest tests/test_thumbnails.py -q` failed red, then passed.
- `docker compose run --rm --build worker pytest tests/test_packager.py -q` failed red, then passed.
- `make test` passed: 56 API tests, 2 worker tests, 1 web test.
- `make lint` passed.
- `make smoke` passed with Alembic `20260712_0007` applied on Postgres.

## Files touched
- `apps/api/alembic/versions/20260712_0007_video_thumbnails.py`
- `apps/api/app/api/thumbnails.py`
- `apps/api/app/services/thumbnails.py`
- `apps/api/app/db/models.py`
- `workers/media/media_worker/packager.py`
- `workers/media/media_worker/repository.py`
- `apps/web/app/studio/videos/[videoId]/thumbnail-manager.tsx`

## Handoff / risks
- Cross-sector interface: cards and playback use `/videos/{video_id}/thumbnail`; legacy HLS thumbnail paths remain available only for old stored videos.
- Custom thumbnails are limited to JPEG/PNG, 5 MiB, and dimensions from 64 to 8192 pixels.
- Next rollout issue is Phase 1 Issue 11: Admin Reports And Moderation.
