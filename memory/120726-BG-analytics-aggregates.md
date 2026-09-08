# 120726-BG-analytics-aggregates

Sector: B - Core API and Database; G - Observability, Admin, and Operations; A - Product and Web App Shell
Agent: Codex
Date: 12-07-2026
Branch/Commit: docs/fullplatform-rollout (pending commit)

## What changed
- Added `video_daily_metrics` and `creator_daily_metrics` via Alembic revision `20260712_0009`.
- Added deterministic date-range aggregation from raw impressions and counted views, plus a Studio analytics API/page.
- Added protected HTTP and `make analytics-rebuild` operations paths backed by the same rebuild service.

## Decisions / ADR notes
- Decision: raw `video_impressions` and `video_views` remain the source of truth; daily tables are replaceable derived data.
- Reason: rerunning a date range must be deterministic and cannot double-count metrics.
- Decision: watch time sums counted-view positions until progress-ping events exist.

## Validation
- `docker compose run --rm api alembic upgrade head`
- `make analytics-rebuild DATE_FROM=2026-07-01 DATE_TO=2026-07-12`
- `make test` (60 API, 2 worker, 1 web tests)
- `make lint`
- `make smoke`
- `npm --workspace apps/web run build`

## Files touched
- apps/api/alembic/versions/20260712_0009_daily_metrics.py
- apps/api/app/services/analytics.py
- apps/api/app/api/studio_analytics.py
- apps/api/app/commands/rebuild_analytics.py
- apps/web/app/studio/analytics/page.tsx
- docs/architecture/events-and-analytics.md

## Handoff / risks
- Cross-sector interfaces: `GET /studio/analytics?days=1..90`, `POST /admin/analytics/rebuild?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD`, and `make analytics-rebuild DATE_FROM=... DATE_TO=...`.
- Daily rebuild currently reads raw event rows in application memory, which is appropriate for the single-node platform stage. Add database-side bucketing or incremental checkpoints before high-volume production operation.
