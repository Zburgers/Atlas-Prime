# Accessibility polish

Sector: A product web app shell and H testing/devex
Agent: Codex
Date: 15-07-2026
Branch/Commit: docs/fullplatform-rollout

## What changed
- Added skip navigation, visible keyboard focus treatment, and 44px primary control targets.
- Updated mobile navigation to preserve every primary route in a horizontally scrollable row and protected long headings from overflow.
- Corrected the new asynchronous client loaders to follow the existing deferred-loading pattern required by frontend lint.

## Decisions / ADR notes
- No ADR-level decision.
- Reason: The existing dark operational UI remains intact while keyboard and mobile behavior now has explicit, testable safeguards.

## Validation
- `npm --workspace apps/web run lint`
- `npm --workspace apps/web run build`
- `make lint` and `make test` (67 API tests, 3 worker tests, web test passed)
- `make smoke` (all services healthy; Wave 3 ready and failure media paths passed)

## Files touched
- `apps/web/app/layout.tsx`
- `apps/web/app/globals.css`
- `apps/web/app/library/library-client.tsx`
- `apps/web/app/subscriptions/subscriptions-client.tsx`

## Handoff / risks
- This pass is CSS and semantic behavior only; no product API or media contract changed.
