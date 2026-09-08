# 050826-C-atomic-upload-claim

Sector: C upload ingest and storage
Agent: Codex
Date: 05-08-2026
Branch/Commit: docs/fullplatform-rollout (local)

## What changed
- Replaced upload read-then-write status mutation with a conditional database claim from `draft` or `failed` to `uploading`.
- Assigned and persisted an active processing generation at claim time; queued jobs inherit that generation.
- Rejected concurrent or already-uploading claims with HTTP 409 before storage and queue side effects.
- Fenced upload failure updates to the matching active generation.

## Decisions / ADR notes
- Decision: Only `draft` and `failed` videos may claim a new original upload; `uploading` is never an accepted starting state.
- Reason: A single compare-and-set update makes ownership deterministic under concurrent requests.
- Alternatives considered: Application-side read-then-write was rejected because it permits duplicate storage and queue side effects.

## Validation
- `docker compose run --rm --build api pytest tests/test_video_api.py -q` (34 passed)
- `git diff --check` (passed)
- `ruff` check not run: the API image does not include the `ruff` executable.

## Files touched
- `apps/api/app/services/uploads.py`
- `apps/api/tests/test_video_api.py`

## Handoff / risks
- Plan 2 Task 2.3 must carry `active_processing_generation` through the Celery payload and assert payload parity.
- The implementation uses SQL `UPDATE ... RETURNING`; PostgreSQL is authoritative for production concurrency behavior.
