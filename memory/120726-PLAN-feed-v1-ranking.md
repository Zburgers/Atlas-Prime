# 120726-PLAN-feed-v1-ranking

Sector: Cross-sector platform rollout
Agent: Codex
Date: 12-07-2026
Branch/Commit: docs/fullplatform-rollout

## What changed
- Implemented Phase 1 Issue 8 with deterministic Home Feed V1 ranking.
- Added `/feed/home` with `request_id`, `surface`, `rank`, `score`, `reason`, and `algorithm_version`.
- Updated the homepage to consume the feed response and pass feed request IDs into impression logging.
- Updated the rollout plan so Issue 9 Recommendation Event Foundation is the next implementation unit.

## Decisions / ADR notes
- Decision: Home Feed V1 ranks public ready videos with a deterministic freshness plus quality score.
- Reason: This creates an auditable product contract before adding persisted recommendation request/result logging.
- Alternatives considered: Personalized ranking and ML recommendations remain deferred.

## Validation
- `docker compose run --rm --build api pytest tests/test_feed.py -q` failed red before `app.domain.ranking` existed, then passed.
- `docker compose run --rm --build web-test npm --workspace apps/web run lint` passed.
- `make test` passed: 53 API tests, 2 worker tests, 1 web test.
- `make lint` passed.
- `make smoke` passed against the live Compose stack.
- `curl -fsS 'http://127.0.0.1:8000/feed/home?page_size=3&request_id=live-feed-probe'` returned the expected feed response shape.
- `curl -fsS http://127.0.0.1:3001/` rendered the homepage.

## Files touched
- `apps/api/app/domain/ranking.py`
- `apps/api/app/api/feed.py`
- `apps/api/app/services/feed.py`
- `apps/api/app/schemas/feed.py`
- `apps/api/app/main.py`
- `apps/api/tests/test_feed.py`
- `apps/web/app/components/video-api.ts`
- `apps/web/app/components/video-list.tsx`
- `docs/plans/02-fullplatform-vision.md`

## Handoff / risks
- Next rollout issue is Phase 1 Issue 9: Recommendation Event Foundation.
- Feed V1 is global and non-personalized; watched/hidden/limited-content exclusions are not implemented yet.
- Recommendation request/result persistence should reuse the existing feed `request_id`, `rank`, and `algorithm_version` fields.
