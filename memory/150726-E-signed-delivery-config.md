# 150726-E-signed-delivery-config

Sector: E delivery and deployment
Agent: Codex
Date: 15-07-2026
Branch/Commit: docs/fullplatform-rollout (pending commit)

## What changed
- Added signed-delivery mode, public media endpoint, token secret, and bounded TTL configuration to API config and Compose.
- Kept proxy delivery as the safe default.

## Decisions / ADR notes
- Decision: Require explicit deployment configuration before signed redirect delivery can be enabled.
- Reason: Docker-internal MinIO origins are not browser-routable and must not be silently used for direct playback.

## Validation
- `docker compose config -q` (passed)
- `docker compose run --rm --build api python -m compileall app` (passed)

## Files touched
- .env.example
- compose.yaml
- apps/api/app/core/config.py

## Handoff / risks
- Production must configure public-origin CORS before enabling signed redirect mode.
