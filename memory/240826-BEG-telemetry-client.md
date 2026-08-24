# 240826-BEG-telemetry-client

Sector: B/E/G
Agent: Luna
Date: 24-08-2026
Branch/Commit: docs/fullplatform-rollout / 7e0142a base; Plan 4.2 uncommitted

## What changed
- Added typed playback-event request construction with valid UUID generation using `crypto.randomUUID()` and a UUIDv4-compatible fallback.
- Watch loads create one telemetry `playback_session_id` per `videoId`; each playback event creates one `event_id` and reuses the same request body for one bounded transient retry.
- Preserved recommendation `request_id`, playback event fields, user-safe UI copy, and the separate VideoView `session_id`.

## Decisions / ADR notes
- Decision: use `useMemo(..., [videoId])` for the per-watch-load telemetry session and keep event identity in the immutable body passed to both attempts.
- Reason: the session resets with the watch route while retries remain idempotent under the Plan 4.1 unique `event_id` contract without adding persistence or cross-page identity.
- Alternatives considered: localStorage, cookies, device identifiers, and unbounded retries were rejected as outside the approved telemetry policy.

## Validation
- `docker compose run --rm --build web-test npm --workspace apps/web test` -> PASS, 6 tests passed.
- `docker compose run --rm --build web-test npm --workspace apps/web run lint` -> PASS, ESLint clean with no warnings.
- `docker compose run --rm web-test npm --workspace apps/web run build` -> PASS, Next.js 16.2.9 production build and TypeScript validation completed.
- `git diff --check` -> PASS.
- No full-stack smoke or Plan 4 completion claim; no commit or push performed.

## Files touched
- `apps/web/app/components/video-api.ts`
- `apps/web/app/watch/[videoId]/watch-client.tsx`
- `apps/web/tests/smoke.test.js`
- `memory/240826-BEG-telemetry-client.md`

## Handoff / risks
- Backend Plan 4.1 now requires identity fields on playback-event writes; the watch page supplies them and never uses the playback event UUID as the VideoView `session_id`.
- The existing `apps/web/app/components/video-list.tsx` `card_click` caller still posts a legacy event body and was intentionally left outside the requested 4.2 write set; parent review should decide whether that non-watch caller needs the same identity contract before broader qualification.
- Rate limiting, retention, aggregate telemetry health, full-stack smoke, and Plan 4 completion remain later work.
