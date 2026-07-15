# 150726-DBG-processing-stage-metadata

Sector: D/B/G media processing, API, and status UI
Agent: Codex
Date: 15-07-2026
Branch/Commit: docs/fullplatform-rollout (pending commit)

## What changed
- Added durable processing-job stages for queued, download, probe, package, upload, complete, and failed work.
- Returned the stage through processing responses and rendered the active worker activity in the shared frontend status panel.

## Decisions / ADR notes
- Decision: Model worker progress as a job stage rather than expanding the canonical video lifecycle.
- Reason: The existing lifecycle remains stable while creators and operators gain precise, durable processing visibility.

## Validation
- `make db-upgrade` (migration applied)
- `make lint` (passed)
- `make test` (passed)
- `make smoke` (passed: ready video and corrupt-media failure path)

## Files touched
- apps/api/alembic/versions/20260715_0014_processing_job_stage.py
- apps/api/app/db/models.py
- apps/api/app/schemas/videos.py
- workers/media/media_worker/repository.py
- workers/media/media_worker/celery_app.py
- apps/web/app/components/status-ui.tsx

## Handoff / risks
- `ProcessingJobResponse.stage` is now an API and frontend contract; new worker phases must use the defined stage values.
- Signed object/CDN delivery and retention lifecycle work remain Phase 4 follow-ups after the proxy and worker hardening slices.
