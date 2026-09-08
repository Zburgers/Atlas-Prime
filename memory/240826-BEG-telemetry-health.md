# 240826-BEG-telemetry-health

Sector: G observability/admin ops and B API
Agent: Luna
Date: 24-08-2026
Branch/Commit: docs/fullplatform-rollout at 6ee3323 (uncommitted changes)

## What changed
- Added protected `GET /admin/telemetry` with aggregate accepted, duplicate, rate-limited, purged, retention-cutoff, and status fields only.
- Added best-effort Redis counters under `atlas:telemetry:metrics:v1:*`; event, admission, and retention outcomes increment only at their approved boundaries.
- Added an independent aggregate-only telemetry panel to the admin dashboard with sanitized degraded/unavailable handling.

## Decisions / ADR notes
- Decision: telemetry health counters are ephemeral operational metrics since Redis state reset, not durable analytics facts.
- Reason: operator visibility must not add identifiers or a second durable event store, and metric failures must never affect playback or ingestion correctness.
- Alternatives considered: none; the approved Redis namespace and aggregate contract were retained.

## Validation
- `docker compose run --rm --build api pytest tests/test_recommendation_logging.py tests/test_analytics_events.py tests/test_telemetry_retention.py -q` -> `26 passed in 8.10s`.
- `docker compose run --rm api pytest tests/test_analytics_worker.py -q` -> `4 passed in 1.29s`.
- `docker compose run --rm api python -m compileall -q ...` -> passed with no output.
- `ruff check` on touched API files/tests -> `All checks passed!` (host binary; the API container does not include `ruff`).
- `docker compose run --rm --build web-test npm --workspace apps/web test` -> 8 passed, 0 failed.
- `docker compose run --rm --build web-test npm --workspace apps/web run lint` -> passed.
- `docker compose run --rm web-test npm --workspace apps/web run build` -> passed; Next.js build and TypeScript completed.
- `git diff --check` -> passed.

## Files touched
- `apps/api/app/services/telemetry_metrics.py`
- `apps/api/app/api/admin.py`, `apps/api/app/api/videos.py`, `apps/api/app/schemas/videos.py`
- `apps/api/app/commands/purge_telemetry.py`, `apps/api/app/worker/analytics.py`
- `apps/api/tests/test_recommendation_logging.py`, `apps/api/tests/test_analytics_events.py`, `apps/api/tests/test_telemetry_retention.py`, `apps/api/tests/test_analytics_worker.py`
- `apps/web/app/components/video-api.ts`, `apps/web/app/admin/admin-dashboard.tsx`, `apps/web/tests/smoke.test.js`

## Handoff / risks
- The admin contract intentionally exposes no event, session, request, user, video, IP, or raw-row data. Missing Redis values read as zero; Redis read failure returns aggregate nulls with a policy cutoff and `degraded` status.
- Metric writes use the existing broker Redis URL, a separate identifier-free namespace, a one-second socket timeout, and swallowed/logged failures. No Plan 4.6 docs/index or full-stack smoke claim is included.
- Parent should review the uncommitted diff and rerun any broader API/full-stack gates before committing.
