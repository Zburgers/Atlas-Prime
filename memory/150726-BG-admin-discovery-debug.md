# Admin discovery debug

Sector: B core API/database and G observability
Agent: Codex
Date: 15-07-2026
Branch/Commit: docs/fullplatform-rollout

## What changed
- Added protected admin recommendation list/detail and search-debug endpoints.
- Reused persisted recommendation results and existing event joins without exposing requester identity or private media.

## Decisions / ADR notes
- No ADR-level decision.
- Reason: Phase 3 requires inspectable discovery health; persisted request/result logs already provide the source of truth.

## Validation
- `uv run pytest apps/api/tests/test_recommendation_logging.py -q` (3 passed)

## Files touched
- `apps/api/app/api/admin.py`
- `apps/api/app/services/recommendation_logging.py`
- `apps/api/app/schemas/feed.py`
- `apps/api/tests/test_recommendation_logging.py`
- `docs/architecture/search-and-ranking.md`

## Handoff / risks
- The API is complete; add the admin dashboard panel in a separate frontend commit so operators can use the endpoints visually.
