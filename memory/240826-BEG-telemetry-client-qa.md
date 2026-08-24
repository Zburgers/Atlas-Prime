# 240826-BEG-telemetry-client-qa

Sector: B/E/G
Agent: Luna
Date: 24-08-2026
Branch/Commit: docs/fullplatform-rollout / 7e0142a base; Plan 4.2 and QA changes uncommitted

## What changed
- Fixed the home-feed `VideoCard` `card_click` producer, which still sent only `event_type` and `request_id` after Plan 4.1 made playback identity fields required.
- Added one component-scoped `playback_session_id` per mounted card and one `event_id` per click using the shared typed telemetry helpers.
- Added a focused source-contract test and confirmed the watch and card-click producers are the only frontend `/events` posts.

## Decisions / ADR notes
- Decision: keep card telemetry state in React component state and retain the existing fire-and-forget click handlers.
- Reason: this repairs the HTTP 422 integration defect without persistence, cross-page identity, navigation changes, or visual/UI changes.
- Parent review caught the defect before commit; no backend or watch-page behavior was changed.

## Validation
- `docker compose run --rm --build web-test npm --workspace apps/web test` -> PASS, 7 tests passed.
- `docker compose run --rm --build web-test npm --workspace apps/web run lint` -> PASS, ESLint clean.
- `docker compose run --rm web-test npm --workspace apps/web run build` -> PASS, Next.js 16.2.9 production build and TypeScript validation completed.
- `git diff --check` -> PASS.
- `rg` event-producer scan -> PASS; only watch-client and video-list card-click producers remain, both with identity-bearing request bodies.
- No commit, push, Plan 4 completion, or full-stack smoke claim.

## Files touched
- `apps/web/app/components/video-list.tsx`
- `apps/web/tests/smoke.test.js`
- `memory/240826-BEG-telemetry-client-qa.md`

## Handoff / risks
- The card-click producer now satisfies the backend `playback_session_id` and `event_id` contract while preserving `request_id` and best-effort navigation.
- Existing Plan 4.2 watch/client helper changes remain uncommitted in the worktree for parent review.
- Rate limiting, retention, aggregate telemetry health, full-stack smoke, and Plan 4 completion remain out of scope.
