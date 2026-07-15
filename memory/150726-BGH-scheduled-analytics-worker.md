# Scheduled analytics worker

Sector: B core API/database, G observability, and H testing/devex
Agent: Codex
Date: 15-07-2026
Branch/Commit: docs/fullplatform-rollout

## What changed
- Added an `analytics`-queue Celery worker and a single Beat scheduler to rebuild current and previous UTC daily metrics at 00:05 UTC.
- Kept media processing isolated on the existing `media` queue and reused the deterministic analytics rebuild service.

## Decisions / ADR notes
- Decision: Rebuild a two-day window each night.
- Reason: The source events are immutable and the existing rebuild is idempotent, so this absorbs delayed writes without incremental checkpoint state.

## Validation
- `uv run pytest apps/api/tests/test_analytics_worker.py -q` (3 passed)
- `docker compose config -q`
- `make lint && make test` (73 API tests, 3 media-worker tests, web checks passed)
- `npm --workspace apps/web run build` (14 routes passed)
- `make smoke` (media lifecycle passed; analytics worker healthy and Beat running)
- `docker compose exec -T analytics-worker python -c "from app.worker.analytics import rebuild_recent_daily_metrics; print(rebuild_recent_daily_metrics.run(1))"` (live database rebuild passed)

## Files touched
- `apps/api/app/worker/analytics.py`
- `apps/api/tests/test_analytics_worker.py`
- `compose.yaml`
- `docs/architecture/events-and-analytics.md`

## Handoff / risks
- Run exactly one `analytics-beat` scheduler per environment; duplicate Beats would enqueue duplicate, though still idempotent, rebuilds.
