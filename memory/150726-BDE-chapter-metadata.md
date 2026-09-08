# 150726-BDE-chapter-metadata

Sector: B/D/E API, media metadata, and playback
Agent: Codex
Date: 15-07-2026
Branch/Commit: docs/fullplatform-rollout (pending commit)

## What changed
- Added ordered, owner-managed video chapters with strict increasing start times and duration bounds when media duration is known.
- Exposed chapters in playback metadata and added an accessible Studio editor for creating, ordering, removing, and saving chapters.

## Decisions / ADR notes
- Decision: Use owner-only replace-all chapter updates and expose the saved ordered list through playback metadata.
- Reason: This keeps ordering deterministic, preserves API-owned playback behavior, and avoids partial reorder races.

## Validation
- Test-first API contract: verified missing chapter endpoints failed before implementation.
- `make db-upgrade` (migration applied)
- `make lint` (passed)
- `make test` (passed)
- `make smoke` (passed: ready video and corrupt-media failure path)

## Files touched
- apps/api/alembic/versions/20260715_0015_video_chapters.py
- apps/api/app/services/chapters.py
- apps/api/app/api/studio.py
- apps/api/app/api/videos.py
- apps/web/app/studio/videos/[videoId]/chapter-manager.tsx

## Handoff / risks
- Playback metadata now includes `chapters`; clients should treat `start_seconds` as a fixed three-decimal string.
- The current Studio editor preserves entered row order; richer drag-and-drop reordering is intentionally deferred.
