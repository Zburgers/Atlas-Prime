# Card click events

Sector: A product web app shell, B core API/database, and G observability
Agent: Codex
Date: 15-07-2026
Branch/Commit: docs/fullplatform-rollout

## What changed
- Added request-attributed `card_click` events to feed-card navigation.
- Exposed clicks separately from playback events in recommendation debug joins.

## Decisions / ADR notes
- No ADR-level decision.
- Reason: The Phase 3 event spine requires clicks to be distinguishable from impressions and subsequent playback.

## Validation
- `uv run pytest apps/api/tests/test_recommendation_logging.py -q` (3 passed)
- `npm --workspace apps/web run lint`

## Files touched
- `apps/api/app/schemas/videos.py`
- `apps/api/app/schemas/feed.py`
- `apps/api/app/services/recommendation_logging.py`
- `apps/web/app/components/video-list.tsx`

## Handoff / risks
- Click telemetry is best effort to avoid blocking navigation; playback and counted-view events remain the durable follow-on activity signals.
