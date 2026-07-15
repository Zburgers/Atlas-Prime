# Idempotent worker claim

Sector: D media processing and packaging
Agent: Codex
Date: 15-07-2026
Branch/Commit: docs/fullplatform-rollout

## What changed
- Made worker start transition atomically claim only queued video-processing jobs for queued videos.
- Duplicate or stale Celery deliveries return `skipped` before download, packaging, or output mutation.

## Decisions / ADR notes
- Decision: Use the processing-job row as the idempotency claim.
- Reason: It is transactional with video lifecycle state and avoids extra deduplication storage.

## Validation
- `docker compose run --rm --build worker pytest tests/test_repository.py -q` (2 passed)

## Files touched
- `workers/media/media_worker/repository.py`
- `workers/media/media_worker/celery_app.py`
- `workers/media/tests/test_repository.py`

## Handoff / risks
- Failed jobs remain explicitly retryable through Studio, which creates a fresh queued job rather than reusing a consumed job.
