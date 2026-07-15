# Discovery ranking

Sector: A product web app shell, B core API/database, and G observability
Agent: Codex
Date: 15-07-2026
Branch/Commit: docs/fullplatform-rollout

## What changed
- Added persisted, request-scoped `trending-v1` and `related-v1` feed responses with ranks, scores, and reasons.
- Added the Trending page and watch-next related-video panel; browser navigation carries each feed request ID into existing impression and playback telemetry.

## Decisions / ADR notes
- Decision: Use deterministic freshness and engagement scoring, with a fixed same-channel priority for related videos.
- Reason: It satisfies the Phase 3 discovery contract while preserving explainability and avoiding premature personalized or ML ranking.

## Validation
- `uv run pytest apps/api/tests/test_feed.py apps/api/tests/test_recommendation_logging.py -q`
- `npm --workspace apps/web run lint`
- `npm --workspace apps/web run build` (14 routes, including `/trending`)
- `make lint && make test` (69 API tests, 3 worker tests, web lint/test passed)
- `make smoke` (all containers healthy; Wave 3 ready and failed-media paths passed)

## Files touched
- `apps/api/app/services/feed.py`
- `apps/api/app/domain/ranking.py`
- `apps/api/app/api/feed.py`
- `apps/api/app/api/videos.py`
- `apps/web/app/trending/trending-client.tsx`
- `apps/web/app/watch/[videoId]/watch-client.tsx`
- `docs/architecture/search-and-ranking.md`

## Handoff / risks
- Related-video ordering prioritizes same-channel public content; cross-channel semantic similarity is deliberately deferred until the planned candidate-generation phase.
- Feed result persistence currently records the requested page; pagination beyond the first page retains the existing recommendation logging contract.
