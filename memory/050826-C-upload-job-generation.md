# 050826-C-upload-job-generation

Sector: C upload/ingest/storage
Agent: /root/plan2_task23
Date: 05-08-2026
Branch/Commit: local Plan 2 Task 2.3 work

## What changed
- Propagated the upload transaction's processing generation through `ProcessingQueue.enqueue_video_processing` into the Celery kwargs.
- Added an upload integration assertion that the active video generation, persisted job generation, and queued payload are identical; public upload response remains redacted.

## Decisions / ADR notes
- Decision: Processing jobs are bound to the immutable generation selected by the upload claim.
- Reason: Later worker transitions can reject stale or redelivered work without allowing a newer upload to be mutated.
- Alternatives considered: None; this follows the indexed Plan 2 generation contract.

## Validation
- `docker compose run --rm --build api pytest tests/test_video_api.py -q` (34 passed)
- `docker compose run --rm api pytest -q` (105 passed)
- `python -m compileall -q apps/api/app/services apps/api/tests`

## Files touched
- `apps/api/app/services/processing_queue.py`
- `apps/api/app/services/uploads.py`
- `apps/api/tests/test_video_api.py`

## Handoff / risks
- The worker task currently accepts only `video_id`, `job_id`, and `original_storage_key`; Plan 2 Task 2.4 must add and fence its `generation` argument before this payload can run against the worker.
- Studio retry enqueue still uses the pre-generation call shape and should be reconciled when retry generation handling is addressed.
