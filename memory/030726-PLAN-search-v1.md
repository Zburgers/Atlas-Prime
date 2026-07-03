# 030726-PLAN-search-v1

Sector: Cross-sector platform rollout
Agent: Codex
Date: 03-07-2026
Branch/Commit: docs/fullplatform-rollout

## What changed
- Implemented Phase 1 Issue 4: Search V1.
- Added `GET /search?q=...` with card-safe public video results.
- Added a header search form and `/search` results page.
- Marked Issue 4 complete in `docs/plans/02-fullplatform-vision.md` and moved the recommended next unit to Issue 5.

## Decisions / ADR notes
- Decision: Search V1 returns public `ready` videos only; private, unlisted, and non-ready videos are excluded even for signed-in users.
- Reason: Search is a public discovery surface and must preserve the browse privacy boundary.
- Decision: Production search uses PostgreSQL full-text search over title, description, channel display name, and channel handle, with a SQLite-compatible fallback for the current API tests.
- Reason: The platform plan calls for Postgres FTS, while the repo's focused API tests still run against SQLite.

## Validation
- `docker compose run --rm --build api pytest tests/test_search.py -q`
- `docker compose run --rm --build api pytest -q`
- `docker compose run --rm --build web-test npm --workspace apps/web run lint`
- `make test`
- `make lint`
- `make smoke`
- Live Postgres FTS probe through `GET /search` with a temporary public ready video, followed by cleanup.
- `git diff --check`

## Files touched
- `apps/api/app/api/search.py`
- `apps/api/app/main.py`
- `apps/api/app/schemas/search.py`
- `apps/api/app/services/search.py`
- `apps/api/tests/test_search.py`
- `apps/web/app/components/app-header.tsx`
- `apps/web/app/components/video-api.ts`
- `apps/web/app/globals.css`
- `apps/web/app/search/page.tsx`
- `apps/web/app/search/search-client.tsx`
- `docs/plans/02-fullplatform-vision.md`
- `memory/030726-PLAN-search-v1.md`

## Handoff / risks
- Next recommended implementation unit is Phase 1, Issue 5: Likes And Watch Later.
- Search V1 has no generated tsvector column or GIN index yet; add an indexed search vector when public inventory grows enough for performance work.
