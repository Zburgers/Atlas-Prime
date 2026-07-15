# Partial HLS cleanup

Sector: D media processing and packaging
Agent: Codex
Date: 15-07-2026
Branch/Commit: docs/fullplatform-rollout

## What changed
- Added deterministic `processed/{video_id}/hls/` prefix cleanup after worker failures.
- Cleanup errors are logged and do not replace the original processing failure.

## Decisions / ADR notes
- Decision: Delete only the HLS prefix.
- Reason: Originals and custom thumbnail paths must survive a failed reprocess.

## Validation
- `docker compose run --rm --build worker python -m compileall media_worker tests`
- `git diff --check`

## Files touched
- `workers/media/media_worker/storage.py`
- `workers/media/media_worker/celery_app.py`

## Handoff / risks
- Object-store cleanup is prefix-bounded and pagination-aware; lifecycle retention for non-failed old outputs remains separate future work.
