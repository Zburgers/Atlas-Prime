# 050826-BCD-processing-generation-schema

Sector: B/C/D/H
Agent: plan2_task21
Date: 05-08-2026
Branch/Commit: docs/fullplatform-rollout (local)

## What changed
- Added nullable `videos.active_processing_generation` and non-null `video_processing_jobs.generation` UUID fields.
- Added a PostgreSQL partial unique index allowing one queued/running job per video.
- Added deterministic migration backfill and downgrade; older active jobs are marked failed before index creation.
- Added ORM metadata coverage for generation columns and the active-job index.

## Decisions / ADR notes
- Decision: Preserve the newest queued/running job by `(created_at DESC, id DESC)` during backfill.
- Reason: Existing duplicate active jobs must be made safe before enforcing uniqueness without nondeterministic selection.
- Alternatives considered: Random UUID backfill was rejected because reruns would not be reproducible.

## Validation
- `docker compose run --rm --build api pytest tests/test_video_status.py -q` — 3 passed.
- `docker compose run --rm --build api alembic upgrade head` — passed.
- `docker compose run --rm api alembic downgrade 20260715_0016 && docker compose run --rm api alembic upgrade head` — passed.
- `git diff --check` — passed.

## Files touched
- `apps/api/app/db/models.py`
- `apps/api/alembic/versions/20260805_0017_processing_generations.py`
- `apps/api/tests/test_video_status.py`

## Handoff / risks
- Later Plan 2 tasks must populate and propagate one generation across upload, queue, and worker updates.
- The partial unique index is PostgreSQL-specific; model metadata keeps the predicate explicit for schema parity.
- No upload or worker behavior was changed in this task.
