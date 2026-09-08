# 030726-PLAN-reactions-watch-later

Sector: Cross-sector platform rollout
Agent: Codex
Date: 03-07-2026
Branch/Commit: docs/fullplatform-rollout

## What changed
- Implemented Phase 1 Issue 5 with video likes and watch-later saves.
- Added `video_reactions`, `video_saves`, and public `like_count` storage.
- Added signed-in engagement endpoints and watch-page controls.
- Exposed like counts on public video cards without listing private videos.

## Decisions / ADR notes
- Decision: Likes are public aggregate counts on accessible video responses; watch-later is private per-viewer state.
- Reason: This keeps public discovery useful while preserving viewer save state behind auth.
- Alternatives considered: Deriving counts from reaction rows on every list query was deferred to avoid heavier public-list queries.

## Validation
- `docker compose run --rm --build api pytest tests/test_reactions.py -q` passed.
- `docker compose run --rm --build web-test npm --workspace apps/web run lint` passed.
- `make test` passed: 44 API tests, 2 worker tests, 1 web test.
- `make lint` passed.
- `make smoke` passed and applied Alembic `20260703_0004` on Postgres.

## Files touched
- `apps/api/alembic/versions/20260703_0004_video_reactions_saves.py`
- `apps/api/app/db/models.py`
- `apps/api/app/services/reactions.py`
- `apps/api/app/api/videos.py`
- `apps/api/app/schemas/videos.py`
- `apps/api/tests/test_reactions.py`
- `apps/web/app/watch/[videoId]/watch-client.tsx`
- `apps/web/app/components/video-api.ts`
- `apps/web/app/components/video-list.tsx`
- `docs/plans/02-fullplatform-vision.md`

## Handoff / risks
- Next rollout issue is Phase 1 Issue 6: Creator Studio Video Manager.
- No watch-later library page exists yet; this entry only stores and toggles save state from the watch page.
- Like count is denormalized and guarded by idempotent service paths plus a nonnegative check constraint.
