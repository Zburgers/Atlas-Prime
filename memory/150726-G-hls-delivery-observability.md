# 150726-G-hls-delivery-observability

Sector: G - Playback and delivery
Agent: Codex
Date: 15-07-2026
Branch/Commit: docs/fullplatform-rollout (pending commit)

## What changed
- Added a validated `X-Request-ID` request/response correlation header for API traffic.
- Logged HLS authorization denials separately from missing processed HLS assets, with the request ID on both log paths.

## Decisions / ADR notes
- Decision: Keep API-proxied HLS delivery and add observability at the API boundary.
- Reason: This satisfies Delivery D1 while preserving private-by-default checks and the existing browser delivery contract.

## Validation
- `docker compose run --rm api pytest tests/test_video_api.py -q` (24 passed)
- `make lint` (passed)
- `make test` (passed)

## Files touched
- apps/api/app/main.py
- apps/api/app/api/videos.py
- apps/api/tests/test_video_api.py

## Handoff / risks
- HLS requests now return `X-Request-ID`; callers may supply a safe correlation value or receive a generated one.
- Delivery D2 signed playback/CDN remains intentionally deferred; continue only after the proxy hardening and lifecycle work are complete.
