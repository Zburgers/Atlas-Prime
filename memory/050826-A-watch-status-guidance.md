# 050826-A-watch-status-guidance

Sector: A - Product and Web App Shell
Agent: plan1_task15
Date: 05-08-2026
Branch/Commit: docs/fullplatform-rollout (local commit pending)

## What changed
- Replaced the watch-page D/E ownership copy with user-safe guidance for queued, processing, ready, failed, and not-ready states.
- Removed worker/sector implementation wording from shared processing-status hints while retaining sanitized API failure text.
- Added a web smoke assertion preventing stale process-internal copy and checking failure-message rendering.

## Decisions / ADR notes
- Decision: Keep processing implementation ownership out of product-facing copy; expose lifecycle state and sanitized failure guidance only.
- Reason: Users need actionable status without internal sector boundaries or worker details.

## Validation
- `docker compose run --rm --build web-test npm --workspace apps/web test` (5 passed)
- `docker compose run --rm --build web-test npm --workspace apps/web run build` (Next.js production build passed)

## Files touched
- `apps/web/app/watch/[videoId]/watch-client.tsx`
- `apps/web/app/components/status-ui.tsx`
- `apps/web/tests/smoke.test.js`

## Handoff / risks
- The watch page still relies on the API's existing sanitized `failure_message`; no backend failure contract was changed.
- No playback or processing internals were changed; this closes Plan 1 Task 1.5 only.
