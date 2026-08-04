# 050826-D-processing-generation-fencing

Sector: D — Media Processing and HLS Packaging
Agent: Codex
Date: 05-08-2026
Branch/Commit: docs/fullplatform-rollout (local, pending commit)

## What changed
- Carried the processing generation through `process_video` and fenced worker claims, stages, success, and failure updates by job ID, generation, running status, and active video generation.
- Made terminal repository methods return an applied boolean; stale or redelivered tasks log and exit without changing video state.
- Wrapped all multi-step repository transitions in rollback-safe transactions when any fence predicate loses.
- Updated studio retry processing to allocate a fresh generation and pass it to the queue.

## Decisions / ADR notes
- Decision: A retry creates a new immutable job generation and becomes the video's active generation.
- Reason: Prevent stale Celery deliveries from finalizing or failing a newer processing attempt while preserving late acknowledgements and one-job claim behavior.
- Alternatives considered: Automatic retries remain out of scope; bounded recovery is Plan 2.5.

## Validation
- `docker compose run --rm --build worker pytest tests/test_repository.py -q` — 11 passed, including rollback assertions for each multi-step transition.
- `PYTHONPATH=apps/api pytest -q apps/api/tests/test_studio.py apps/api/tests/test_video_api.py` — 40 passed.
- `git diff --check` — pending final commit validation.

## Files touched
- `workers/media/media_worker/repository.py`
- `workers/media/media_worker/celery_app.py`
- `workers/media/tests/test_repository.py`
- `apps/api/app/services/studio.py`
- `apps/api/tests/test_studio.py`

## Handoff / risks
- Plan 2.4 only; do not start stale-job recovery or attempt-scoped storage work before Plan 2.5/2.6.
- Existing HLS cleanup uses the video-level prefix; a stale task that fails after a newer attempt begins can still require the later storage-scope hardening planned outside this task.
