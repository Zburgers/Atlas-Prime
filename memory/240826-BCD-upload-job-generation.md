# 240826-BCD-upload-job-generation

Sector: B/C/D/H
Agent: Luna
Date: 24-08-2026
Branch/Commit: docs/fullplatform-rollout / 6bb8064

## What changed
- Closed the upload/job generation hardening documentation phase at `6bb8064`, atop generation-fencing commits through `0ca718e`.
- Recorded the changed interfaces: `videos.active_processing_generation`, `video_processing_jobs.generation`, and the exact queue payload `video_id`, `job_id`, `generation`, `original_storage_key`.
- Recorded `ATLAS_PROCESSING_STALE_SECONDS` (default 900, minimum 60) and `make processing-recover-stale`; dry run is the default and `ARGS="--apply"` is explicit.

## Decisions / ADR notes
- Decision: stale recovery is bounded, generation/status/`started_at` conditional, and operator-initiated; no automatic retry was added.
- Reason: a stale snapshot must not mutate a newer generation or create an unbounded retry loop.
- Alternatives considered: automatic Celery retry was rejected for this phase.

## Validation
- At `6bb8064`, `make test` passed 115 API tests, 14 worker tests, and 5 web tests.
- At `6bb8064`, `make lint` passed Compose validation, API/worker `compileall`, and web build/lint.
- `WEB_PORT=3002 WEB_SMOKE_URL=http://127.0.0.1:3002 make smoke` passed API/web/worker health, Alembic upgrade, private-by-default and API-mediated/API-proxied contract checks, upload through ready/HLS playback including master/rendition/segment/thumbnail, cross-user denial, and corrupt-media failure.
- The initial default-port smoke was blocked because unrelated `sandlabx-backend` owned `127.0.0.1:3001`; it was not stopped and that attempt is not a pass.
- Documentation checks for this handoff: `git diff --check`, the plan-index completeness command, and targeted C-004/C-005 contradiction checks.

## Files touched
- `docs/api-database.md`
- `docs/PRODUCT_SPEC_AND_ENGINEERING_HANDBOOK.md`
- `docs/plans/README.md`
- `memory/240826-BCD-upload-job-generation.md`

## Handoff / risks
- Plan 3 is READY, not complete. It must consume the generation contract for attempt-scoped publication, cleanup, deletion fencing, and segment binding.
- Live PostgreSQL/process-death/worker concurrency and deployed-runtime qualification remain open. C-006 through C-010 remain Plan 3/4 work; merge, deployment, and release readiness are not claimed.
- Preserve the existing Hallmark, design-taste, and accessibility frontend work; this closeout changed documentation only.
