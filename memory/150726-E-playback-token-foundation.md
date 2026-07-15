# 150726-E-playback-token-foundation

Sector: E delivery and playback
Agent: Codex
Date: 15-07-2026
Branch/Commit: docs/fullplatform-rollout (pending commit)

## What changed
- Added a dependency-free HMAC playback-token codec with video, viewer, expiry, and token-version claims.
- Added test-first coverage for video binding and token-version revocation checks.

## Decisions / ADR notes
- Decision: Use compact signed tokens rather than a new JWT dependency.
- Reason: The delivery gateway only needs short-lived symmetric tokens and constant-time signature verification.

## Validation
- Test-first: verified the token service was absent before implementation.
- `docker compose run --rm --build api pytest tests/test_playback_delivery.py -q` (passed)

## Files touched
- apps/api/app/services/playback_delivery.py
- apps/api/tests/test_playback_delivery.py

## Handoff / risks
- The token secret must be at least 32 characters; no fallback secret is allowed.
- This is foundation only: video token version persistence, manifest delivery routes, and MinIO presigning remain next D2 slices.
