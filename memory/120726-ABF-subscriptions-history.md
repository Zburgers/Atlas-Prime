# Subscriptions and history

Sector: A product web app shell, B core API/database, F auth/access control
Agent: Codex
Date: 12-07-2026
Branch/Commit: docs/fullplatform-rollout

## What changed
- Added channel subscriptions, a public-ready subscription feed, and viewer-scoped watch history.
- Recorded history from authenticated `play` events without changing counted-view semantics.
- Added Library and Subscriptions frontend routes and primary navigation.

## Decisions / ADR notes
- Decision: Use play events for history, not view-count events.
- Reason: History should record viewer intent immediately while counted views retain their quality threshold.

## Validation
- `docker compose run --rm --build api alembic upgrade head`
- `docker compose run --rm --build api pytest tests/test_subscriptions_history.py tests/test_reactions.py tests/test_feed.py -q` (8 passed)
- `npm --workspace apps/web run build`

## Files touched
- `apps/api/app/services/subscriptions.py`
- `apps/api/app/api/library.py`
- `apps/web/app/subscriptions/subscriptions-client.tsx`
- `apps/web/app/library/library-client.tsx`

## Handoff / risks
- Feed pagination and unsubscribe management UI remain suitable follow-ups; this slice supplies the required durable API and basic browser surfaces.
