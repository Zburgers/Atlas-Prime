# 150726-BE-playback-token-rotation

Sector: B/E API and delivery
Agent: Codex
Date: 15-07-2026
Branch/Commit: docs/fullplatform-rollout (pending commit)

## What changed
- Persisted `playback_token_version` on videos and added an owner-only rotation endpoint.
- Rotation increments the durable version that delivery token verification will enforce.

## Decisions / ADR notes
- Decision: Use monotonically increasing per-video token versions.
- Reason: Rotation invalidates all previously minted manifest tokens without storing each token individually.

## Validation
- Test-first endpoint contract passed.
- Alembic upgrade to `20260715_0016` passed.

## Files touched
- apps/api/alembic/versions/20260715_0016_playback_token_version.py
- apps/api/app/db/models.py
- apps/api/app/services/studio.py
- apps/api/app/api/studio.py

## Handoff / risks
- The frontend rotation control and delivery-manifest verification remain next D2 slices.
