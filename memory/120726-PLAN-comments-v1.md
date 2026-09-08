# 120726-PLAN-comments-v1

Sector: Cross-sector platform rollout
Agent: Codex
Date: 12-07-2026
Branch/Commit: docs/fullplatform-rollout

## What changed
- Implemented Phase 1 Issue 7 with top-level video comments.
- Added `video_comments`, comment list/create/delete API, and watch-page comment thread.
- Enforced existing video access rules before listing or creating comments.
- Updated the rollout plan so Issue 8 Feed V1 Ranking is the next implementation unit.

## Decisions / ADR notes
- Decision: Comment deletion is limited to the comment author for V1.
- Reason: The plan defers owner/admin moderation until later moderation work while still supporting user-owned deletion.
- Alternatives considered: Creator/admin moderation delete was deferred to Admin Reports And Moderation.

## Validation
- `docker compose run --rm --build api pytest tests/test_comments.py -q` failed red before routes existed, then passed.
- `docker compose run --rm --build web-test npm --workspace apps/web run lint` passed.
- `make test` passed: 50 API tests, 2 worker tests, 1 web test.
- `make lint` passed.
- `make smoke` passed and applied Alembic `20260712_0005` on Postgres.
- `curl -fsS -H 'X-Atlas-Dev-Clerk-User-Id: smoke-owner' http://127.0.0.1:8000/videos/<ready_video>/comments` returned an empty owner-accessible list.
- Live POST/DELETE comment probe on the smoke ready video returned created comment state and `204` delete.

## Files touched
- `apps/api/alembic/versions/20260712_0005_comments.py`
- `apps/api/alembic/env.py`
- `apps/api/app/db/models.py`
- `apps/api/app/api/comments.py`
- `apps/api/app/services/comments.py`
- `apps/api/app/schemas/comments.py`
- `apps/api/app/main.py`
- `apps/api/tests/test_comments.py`
- `apps/web/app/components/video-api.ts`
- `apps/web/app/watch/[videoId]/watch-client.tsx`
- `apps/web/app/globals.css`
- `docs/plans/02-fullplatform-vision.md`

## Handoff / risks
- Next rollout issue is Phase 1 Issue 8: Feed V1 Ranking.
- Comments are top-level only; replies, edits, moderation queues, and creator/admin deletion are deferred.
- Public comment responses expose only an author display label, not Clerk IDs or internal user IDs.
