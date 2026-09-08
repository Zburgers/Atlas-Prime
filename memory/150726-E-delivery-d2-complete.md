# 150726-E-delivery-d2-complete

Sector: E - Delivery, Playback, and CDN Pathing
Agent: Codex
Date: 15-07-2026
Branch/Commit: docs/fullplatform-rollout

## What changed
- Enforced viewer binding for signed delivery tokens while retaining viewerless anonymous public and unlisted playback.
- Added D2 regressions for private access, expiry, rotation, manifest/segment routing, and public/unlisted behavior; updated the rollout plan with the delivered contract.

## Decisions / ADR notes
- Decision: Treat signed private playback URLs as viewer-bound API delivery credentials, not transferable public links.
- Reason: The Next backend proxy preserves the Clerk session for HLS manifest and segment requests, allowing delivery to retain private-video semantics.

## Validation
- `make lint`
- `make test` (88 API tests, 5 worker tests, 1 web package test)
- `./scripts/smoke-devex.sh` (full-stack smoke passed)
- MinIO CORS preflight verified for allowed and disallowed origins.
- Temporarily enabled signed mode against the local Compose stack and verified API manifest issuance, rendition URI rewriting, segment `307`, signed MinIO object retrieval, and browser-origin CORS headers.

## Files touched
- apps/api/app/api/videos.py
- apps/api/tests/test_video_api.py
- compose.yaml
- docs/plans/02-fullplatform-vision.md

## Handoff / risks
- Production must set `ATLAS_MEDIA_CORS_ALLOWED_ORIGINS`, `MINIO_PUBLIC_ENDPOINT`, and `ATLAS_PLAYBACK_TOKEN_SECRET` before enabling signed mode.
- Earlier issued object redirects remain usable only until their bounded presign expiry; token rotation blocks new manifest and segment authorization immediately.
