# Playback progress events

Sector: E playback and G observability
Agent: Codex
Date: 15-07-2026
Branch/Commit: docs/fullplatform-rollout

## What changed
- Extended validated playback events with seek, bounded progress pings, buffering start/end, and ended states.
- Wired native media events and hls.js quality-level switches into the watch client without changing the existing API-owned HLS delivery path.

## Decisions / ADR notes
- Decision: Emit one progress ping per 15 seconds of media position.
- Reason: Progress is useful for diagnosis and future aggregation, but raw event volume must remain bounded.

## Validation
- `uv run pytest apps/api/tests/test_video_api.py -q` (24 passed)
- `npm --workspace apps/web run lint`
- `npm --workspace apps/web run build` (14 routes passed)

## Files touched
- `apps/api/app/schemas/videos.py`
- `apps/api/tests/test_video_api.py`
- `apps/web/app/watch/[videoId]/watch-client.tsx`
- `docs/architecture/events-and-analytics.md`

## Handoff / risks
- Progress pings are raw telemetry only; daily creator watch-time metrics continue to use counted-view positions until aggregation is deliberately expanded.
