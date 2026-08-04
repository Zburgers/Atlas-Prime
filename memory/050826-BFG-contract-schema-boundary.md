# 050826-BFG-contract-schema-boundary

Sector: B/F/G (API contract, auth boundary, admin debug)
Agent: plan1-task1.2
Date: 05-08-2026
Branch/Commit: docs/fullplatform-rollout (uncommitted handoff)

## What changed
- Removed storage object keys and queue task identifiers from normal video, upload, and playback response schemas.
- Added distinct `VideoDebugResponse` and `RenditionDebugResponse` schemas for protected admin video/debug routes.
- Updated API route serializers and regression assertions for redacted product contracts.

## Decisions / ADR notes
- Decision: Product/creator contracts expose API-owned URLs and domain metadata only; operator/debug contracts may expose storage keys.
- Reason: Prevent internal storage and queue topology from becoming a client dependency or disclosure.
- Alternatives considered: Reusing one response model was rejected because it makes accidental leakage easy.

## Validation
- `docker compose run --rm --build api pytest tests/test_video_api.py tests/test_playback_delivery.py -q` — 33 passed.
- OpenAPI inspection confirmed distinct product/debug schemas and redacted product fields.

## Files touched
- `apps/api/app/schemas/videos.py`
- `apps/api/app/api/videos.py`
- `apps/api/app/api/admin.py`
- `apps/api/tests/test_video_api.py`

## Handoff / risks
- Admin `/admin/videos` and `/admin/videos/{id}/debug` retain storage keys through protected debug schemas.
- Any frontend caller still reading removed upload/storage fields must be handled by Plan 1 Task 1.3.
