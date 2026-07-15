# 150726-E-delivery-d2-contract

Sector: E delivery and playback
Agent: Codex
Date: 15-07-2026
Branch/Commit: docs/fullplatform-rollout (pending commit)

## What changed
- Added the Delivery D2 implementation contract to the authoritative rollout plan.
- Defined signed manifest rewriting plus presigned segment redirects, token version rotation, public media-origin requirements, and validation gates.

## Decisions / ADR notes
- Decision: Keep HLS manifests API-owned and redirect only segment bytes to signed object URLs.
- Reason: Nested HLS URIs require per-request authorization while direct segment redirects remove media-byte load from FastAPI.

## Validation
- Reviewed the current worker HLS layout and Next/FastAPI proxy behavior against the D2 contract.
- `git diff --check` (pending commit validation)

## Files touched
- docs/plans/02-fullplatform-vision.md

## Handoff / risks
- Signed redirect mode needs a browser-routable `MINIO_PUBLIC_ENDPOINT`, CORS policy, and deployment secret; Docker-internal `http://minio:9000` is not valid for browser delivery.
- Token rotation immediately blocks future manifest/segment requests, while already-issued object URLs remain bounded by their short expiry.
