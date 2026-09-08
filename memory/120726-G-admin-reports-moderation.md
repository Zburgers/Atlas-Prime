# 120726-G-admin-reports-moderation

Sector: G - Observability, Admin, and Operations; B - Core API and Database; F - Authentication and Access Control
Agent: Codex
Date: 12-07-2026
Branch/Commit: docs/fullplatform-rollout (pending commit)

## What changed
- Added moderation status to videos/comments plus `content_reports`, `moderation_actions`, and `audit_log_entries` through Alembic revision `20260712_0008`.
- Added user reporting, admin report queue/action/audit endpoints, and `/admin/reports` UI.
- Removed content is excluded from browse, search, channels, new and replayed feeds, direct reads, playback, thumbnails, and comments.

## Decisions / ADR notes
- Decision: configure admin access with `ATLAS_ADMIN_CLERK_USER_IDS`, a comma-separated Clerk user ID allowlist; an empty value denies admin access.
- Reason: the previous admin endpoints accepted every authenticated user and no Clerk role claim contract exists in this deployment.
- Decision: moderation is a separate status from lifecycle and privacy; limited content remains link-watchable but is excluded from discovery.

## Validation
- `docker compose run --rm api alembic upgrade head`
- `make test` (59 API, 2 worker, 1 web tests)
- `make lint`
- `make smoke`
- `npm --workspace apps/web run build`

## Files touched
- apps/api/alembic/versions/20260712_0008_moderation.py
- apps/api/app/api/moderation.py
- apps/api/app/services/moderation.py
- apps/api/app/services/recommendation_logging.py
- apps/web/app/admin/reports/page.tsx
- .env.example

## Handoff / risks
- Cross-sector interfaces: `POST /moderation/reports`; `GET /admin/reports`; `POST /admin/reports/{report_id}/actions`; `GET /admin/audit-log`; environment variable `ATLAS_ADMIN_CLERK_USER_IDS`.
- Configure at least one real Clerk user ID before using admin routes outside test/dev headers. Report creation is API-only; a viewer-facing report control can be added as a later UX increment.
