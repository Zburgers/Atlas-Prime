# 020726-PLAN-fullplatform-rollout

Sector: Cross-sector platform planning
Agent: Codex
Date: 02-07-2026
Branch/Commit: docs/fullplatform-rollout

## What changed
- Replaced `docs/plans/02-fullplatform-vision.md` with a structured post-MVP rollout plan.
- Added the full-platform plan to `docs/README.md` read order.
- Implemented Phase 1 Issue 1: public video card grid and card-safe video list response.
- Updated public listing semantics so `unlisted` ready videos remain direct-link readable but are excluded from public browse.
- Implemented Phase 1 Issue 2: channel data model, default channel creation, channel API, channel-aware cards, and public channel page.
- Implemented Phase 1 Issue 3: raw video impressions, normalized counted views, card view counts, grid impression recording, and watch-page view recording.

## Decisions / ADR notes
- Decision: Preserve the existing A-H sector meanings and use post-MVP platform tracks/issues instead of renaming Sector F/G/H.
- Reason: The current sector manifests are already the repo contract, and the full-platform plan should extend them rather than conflict with them.
- Alternatives considered: Reusing the old vision document's Sector F/G/H labels for search/recommendations/admin, rejected because it conflicts with `docs/sectors/`.
- Decision: `GET /videos` now returns card-safe list items with API-owned `thumbnail_url` instead of the full detail response.
- Reason: Public browse should not expose raw processed storage keys, and the frontend only needs card metadata for the home grid.
- Decision: Users get one default channel with a normalized unique handle, and new videos attach to that channel.
- Reason: Phase 1 needs stable creator identity for video cards, channel pages, search, subscriptions, and Studio.
- Decision: A view is counted once per `video_id` and playback `session_id` after five seconds of playback.
- Reason: This gives the MVP a simple duplicate-suppression rule without introducing user/device fingerprinting or watch-time aggregation yet.
- Decision: Impressions are stored as raw events with `surface`, zero-based `position`, optional `request_id`, and a denormalized counter on `videos`.
- Reason: Search/ranking and creator analytics need event-level data later, while public cards need a cheap count now.

## Validation
- `docker compose run --rm --build api pytest tests/test_analytics_events.py -q`
- `docker compose run --rm --build api pytest tests/test_video_api.py -q`
- `docker compose run --rm --build web-test npm --workspace apps/web run lint`
- `make test`
- `make lint`
- `make smoke`
- `git diff --check`
- `docker compose run --rm --build api pytest tests/test_channels.py -q`
- `docker compose run --rm --build api pytest -q`

## Files touched
- `apps/api/app/api/videos.py`
- `apps/api/app/api/channels.py`
- `apps/api/app/db/models.py`
- `apps/api/app/domain/events.py`
- `apps/api/app/schemas/channels.py`
- `apps/api/app/schemas/videos.py`
- `apps/api/app/services/analytics.py`
- `apps/api/app/services/channels.py`
- `apps/api/app/services/users.py`
- `apps/api/app/services/videos.py`
- `apps/api/tests/test_analytics_events.py`
- `apps/api/tests/test_video_api.py`
- `apps/api/tests/test_channels.py`
- `apps/api/alembic/env.py`
- `apps/api/alembic/versions/20260702_0002_channels.py`
- `apps/api/alembic/versions/20260702_0003_impressions_and_views.py`
- `apps/web/app/components/app-header.tsx`
- `apps/web/app/components/video-api.ts`
- `apps/web/app/components/video-list.tsx`
- `apps/web/app/channels/[handle]/page.tsx`
- `apps/web/app/channels/[handle]/channel-client.tsx`
- `apps/web/app/watch/[videoId]/watch-client.tsx`
- `apps/web/app/globals.css`
- `docs/plans/02-fullplatform-vision.md`
- `docs/README.md`
- `memory/020726-PLAN-fullplatform-rollout.md`

## Handoff / risks
- Next recommended implementation unit is Phase 1, Issue 4: Search V1.
- Existing videos without `channel_id` are backfilled lazily the next time their owner is resolved through the API; the migration intentionally avoids DB-specific UUID generation for historical rows.
- View counts are intentionally session-scoped and threshold-only for this issue; robust anti-abuse, watch-time aggregation, and creator analytics are later rollout issues.
