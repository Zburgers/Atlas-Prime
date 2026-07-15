# Admin discovery dashboard

Sector: A product web app shell and G observability
Agent: Codex
Date: 15-07-2026
Branch/Commit: docs/fullplatform-rollout

## What changed
- Added a recommendation-request list and selected result telemetry panel to the existing admin dashboard.
- The panel uses the protected admin diagnostics API and exposes rank reason, impressions, playback events, and counted views.

## Decisions / ADR notes
- No ADR-level decision.
- Reason: The existing operations dashboard is the correct operator surface for the Phase 3 discovery-debug contract.

## Validation
- `npm --workspace apps/web run lint`
- `npm --workspace apps/web run build` (14 routes passed)

## Files touched
- `apps/web/app/admin/admin-dashboard.tsx`
- `apps/web/app/components/video-api.ts`

## Handoff / risks
- Search diagnostics remain available through `GET /admin/search`; a query form can be added to the dashboard when operators need frequent search-rank investigation.
