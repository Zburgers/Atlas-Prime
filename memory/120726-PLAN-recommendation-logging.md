# 120726-PLAN-recommendation-logging

Sector: Cross-sector platform rollout
Agent: Codex
Date: 12-07-2026
Branch/Commit: docs/fullplatform-rollout

## What changed
- Implemented Phase 1 Issue 9 with durable recommendation requests and ranked recommendation results.
- Replayed a feed request ID from its stored results and added a requester-only debug query with impression, playback-event, and counted-view joins.
- Carried recommendation request IDs from home-feed links into watch-page playback and view telemetry.
- Made API startup apply Alembic before serving traffic; the worker now waits for the API health check.

## Decisions / ADR notes
- Decision: A feed request ID is immutable for its viewer, surface, algorithm version, and pagination parameters.
- Reason: Analytics attribution must describe the exact ranked results shown, not a later re-ranked response.
- Alternatives considered: Mutable refreshes and global debug access were rejected because they weaken auditability and viewer isolation.

## Validation
- `docker compose run --rm --build api pytest tests/test_recommendation_logging.py -q` failed red, then passed: 2 tests.
- `make test` passed: 55 API tests, 2 worker tests, 1 web test.
- `make lint` passed.
- `make smoke` passed with API startup migrations enabled.
- Live API probe returned one request result with `impression_count=1`, `playback_event_count=1`, and `view_count=1` from `/feed/requests/live-recommendation-join-audit/debug`.

## Files touched
- `apps/api/alembic/versions/20260712_0006_recommendation_logging.py`
- `apps/api/app/services/recommendation_logging.py`
- `apps/api/app/services/feed.py`
- `apps/api/app/api/feed.py`
- `apps/api/app/api/videos.py`
- `apps/web/app/components/video-list.tsx`
- `apps/web/app/watch/[videoId]/watch-client.tsx`
- `apps/api/Dockerfile`
- `compose.yaml`

## Handoff / risks
- Cross-sector interface: `request_id` is accepted by playback-event and view payloads; home-feed watch links preserve it as a query parameter.
- Debug feed requests require the same signed-in viewer that created the request; anonymous feed requests remain replayable but have no debug readout.
- Next rollout issue is Phase 1 Issue 10: Thumbnail Manager.
