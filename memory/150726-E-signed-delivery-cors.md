# 150726-E-signed-delivery-cors

Sector: E - Delivery, Playback, and CDN Pathing
Agent: Codex
Date: 15-07-2026
Branch/Commit: docs/fullplatform-rollout

## What changed
- Configured MinIO server CORS through `ATLAS_MEDIA_CORS_ALLOWED_ORIGINS` for signed browser media requests.
- Kept the original and processed buckets private; CORS does not grant object access.

## Decisions / ADR notes
- Decision: Use MinIO's server-level explicit-origin CORS configuration instead of `mc cors set`.
- Reason: The repository's MinIO server returns an S3 "not implemented" response for bucket CORS configuration, while server-level CORS is supported and documented.

## Validation
- `docker compose config -q`
- Recreated MinIO and ran the bootstrap service.
- Verified an `OPTIONS` request from `http://localhost:3001` returns `Access-Control-Allow-Origin`; an unapproved origin does not.

## Files touched
- compose.yaml
- .env.example
- docs/local-dev.md

## Handoff / risks
- Set `ATLAS_MEDIA_CORS_ALLOWED_ORIGINS` to exact deployment browser origins; do not use `*`.
- The next D2 slice covers explicit expiration, token-rotation, and private-access delivery regressions.
