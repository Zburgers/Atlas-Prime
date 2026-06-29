# 290626-G-admin-ops-portal

Sector: G observability, admin, and operations
Agent: Codex
Date: 29-06-2026
Branch/Commit: main / pending local commit

## What changed
- Added protected admin ops endpoints for worker health, Redis media queue depth, recent videos, recent jobs, and per-video debug details.
- Added `/admin` web dashboard for local MVP debugging.
- Added playback event ingestion and structured logs for worker stages, playback errors, and missing HLS assets.
- Added an ops runbook for failure triage.

## Decisions / ADR notes
- Decision: Reuse existing auth, job, video, rendition, and playback event tables instead of adding new observability schema.
- Reason: Sector G only needs MVP debugging visibility; current tables already contain the required state.
- Alternatives considered: Separate metrics/heartbeat tables, deferred until the single-node demo needs historical ops analytics.

## Validation
- `pytest apps/api/tests/test_video_api.py apps/api/tests/test_health_contract.py` (23 passed)
- `npm --workspace apps/web run lint`
- `npm --workspace apps/web run build`
- `npm --workspace apps/web test`
- `make lint`
- `make test`
- `make smoke`
- Manual probe: `curl -fsS http://127.0.0.1:3001/admin` returned the admin page HTML; direct `/admin/ops` curl with dev headers returned 401 because dev auth headers are disabled in the running Clerk-auth API.

## Files touched
- apps/api/app/api/admin.py
- apps/api/app/api/videos.py
- apps/api/app/schemas/videos.py
- apps/api/app/services/processing_queue.py
- apps/web/app/admin/
- apps/web/app/watch/[videoId]/watch-client.tsx
- workers/media/media_worker/celery_app.py
- docs/observability-admin-ops.md
- apps/api/tests/test_video_api.py

## Handoff / risks
- Admin endpoints are protected by existing Clerk/current-user auth, but they do not yet enforce a separate admin role.
- `/admin/ops` uses Celery inspect; if the worker/broker is unreachable it reports degraded state with a sanitized error class.
- Playback telemetry is best-effort from the browser and intentionally does not interrupt playback.
