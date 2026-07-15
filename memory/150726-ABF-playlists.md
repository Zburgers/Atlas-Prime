# Playlists

Sector: A product web app shell, B core API/database, F auth/access control
Agent: Codex
Date: 15-07-2026
Branch/Commit: docs/fullplatform-rollout

## What changed
- Added private-by-default playlists, ordered playlist items, and the documented create/read/add/remove API.
- Added browser routes for playlist creation and playlist playback lists.

## Decisions / ADR notes
- Decision: Permit only public ready approved videos in playlist items.
- Reason: A public playlist must never become a path to private or moderated media.

## Validation
- `docker compose run --rm --build api alembic upgrade head`
- `docker compose run --rm --build api pytest tests/test_playlists.py tests/test_subscriptions_history.py -q` (4 passed)
- `npm --workspace apps/web run build`

## Files touched
- `apps/api/app/services/playlists.py`
- `apps/api/app/api/playlists.py`
- `apps/web/app/playlists/`

## Handoff / risks
- The current UI creates and reads playlists; item management UI is a later ergonomic increment, while the API is complete and ownership-protected.
