# Rendition output metadata

Sector: B core API/database and D media processing
Agent: Codex
Date: 15-07-2026
Branch/Commit: docs/fullplatform-rollout

## What changed
- Added codec, segment count, and output-size fields to `video_renditions`.
- The HLS worker now measures each generated rendition directory and persists its metadata with the ready record.

## Decisions / ADR notes
- No ADR-level decision.
- Reason: Phase 4 needs inspectable rendition outputs without leaking storage paths outside existing owner/admin contracts.

## Validation
- `docker compose run --rm --build worker pytest tests/test_packager.py tests/test_repository.py -q` (4 passed)
- `docker compose run --rm --build api alembic upgrade head`

## Files touched
- `apps/api/alembic/versions/20260715_0013_rendition_metadata.py`
- `apps/api/app/db/models.py`
- `apps/api/app/schemas/videos.py`
- `workers/media/media_worker/packager.py`
- `workers/media/media_worker/repository.py`

## Handoff / risks
- Output size measures the generated local rendition directory before upload; object-store verification remains a future storage lifecycle concern.
