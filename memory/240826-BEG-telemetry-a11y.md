# 240826-BEG-telemetry-a11y

Sector: A product web app shell / accessibility
Agent: Luna
Date: 24-08-2026
Branch/Commit: docs/fullplatform-rollout at 5494bc9 (uncommitted scoped fix)

## What changed
- Fixed the home-feed thumbnail link accessible name to include the visible formatted duration badge when present.
- Reused the same duration value for the badge and accessible label; navigation and card-click telemetry are unchanged.
- Added a focused source regression assertion for duration/name parity.

## Decisions / ADR notes
- Decision: keep the existing semantic link and add the visible duration to its accessible name rather than redesigning the card.
- Reason: resolves Lighthouse `label-content-name-mismatch` with the smallest UI/accessibility change.

## Validation
- `docker compose run --rm web-test npm --workspace apps/web test` -> 8 passed.
- `docker compose run --rm web-test npm --workspace apps/web run lint` -> passed.
- `docker compose run --rm web-test npm --workspace apps/web run build` -> passed; Next.js build and TypeScript completed.
- `git diff --check` -> passed.
- Lighthouse CLI audit: Not run; `lighthouse` is unavailable in the environment. Google Chrome is installed, but no Lighthouse runner was available.

## Files touched
- `apps/web/app/components/video-list.tsx`
- `apps/web/tests/smoke.test.js`

## Handoff / risks
- This is local/browser-oriented evidence only and is not production qualification.
- The source regression proves duration text parity; a parent/browser rerun can confirm the live Lighthouse result on the populated home feed.
