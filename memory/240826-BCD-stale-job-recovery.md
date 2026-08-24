# 240826-BCD-stale-job-recovery

Sector: B/C/D/H
Agent: Luna
Date: 24-08-2026
Branch/Commit: docs/fullplatform-rollout / 0ca718ea5f10dfa37224c6b01ad477fe05ea96d5

## What changed
- Completed bounded stale processing recovery with a 900-second default and 60-second minimum.
- Kept recovery dry-run by default; `--apply` conditionally fails the exact running job generation and matching active video state without enqueueing retries.
- Added Makefile/env usage text and tests for selection, fencing, dry-run, apply, and superseded candidates.

## Decisions / ADR notes
- Decision: Recover each candidate inside a savepoint and require exact job id, video id, generation, running status, started_at, active video generation, and unchanged active video status.
- Reason: A stale snapshot must not fail a job or video after another worker, retry, or lifecycle transition has changed ownership.
- Alternatives considered: Automatic retry was rejected; recovery remains an explicit operator action.

## Validation
- `pytest -q tests/test_processing_recovery.py tests/test_video_status.py tests/test_video_api.py` — 46 passed.
- `docker compose run --rm --build api pytest tests/test_processing_recovery.py -q` — 9 passed.
- `make lint` — passed compose validation, API/worker compileall, web build, and web lint.
- `python -m compileall -q app tests`, `python -m app.commands.recover_stale_jobs --help`, and `git diff --check` — passed.

## Files touched
- `.env.example`
- `Makefile`
- `apps/api/app/core/config.py`
- `apps/api/app/services/processing_queue.py`
- `apps/api/app/commands/recover_stale_jobs.py`
- `apps/api/tests/test_processing_recovery.py`

## Handoff / risks
- New operator interface: `make processing-recover-stale` is dry-run; use `ARGS="--apply"` only after review. `ATLAS_PROCESSING_STALE_SECONDS` is clamped to 60 seconds.
- No schema, worker payload, or frontend changes were made. Apply mode is SQL-fenced and does not retry or enqueue jobs.
- Tests use compiled PostgreSQL statements and a transactional session fake; a live concurrent PostgreSQL recovery race remains a deployment-level qualification step.
