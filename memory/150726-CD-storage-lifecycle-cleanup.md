# 150726-CD-storage-lifecycle-cleanup

Sector: C/D storage and media lifecycle
Agent: Codex
Date: 15-07-2026
Branch/Commit: docs/fullplatform-rollout (pending commit)

## What changed
- Owner video deletion now removes the exact original object and every processed object under the bounded `processed/{video_id}/` prefix before deleting database records.
- Processed-prefix cleanup is paginated and checks S3 multi-delete errors; storage failures keep the video row intact and return a safe cleanup error.

## Decisions / ADR notes
- Decision: Clean object storage before database deletion.
- Reason: A failed cleanup leaves the video retriable instead of silently creating orphaned media objects.

## Validation
- Test-first deletion contract: verified storage cleanup was absent before implementation.
- `make lint` (passed)
- `make test` (passed)
- `make smoke` (passed: ready video and corrupt-media failure path)

## Files touched
- apps/api/app/services/storage.py
- apps/api/app/services/videos.py
- apps/api/app/api/videos.py
- apps/api/tests/test_video_api.py
- apps/api/tests/test_storage.py

## Handoff / risks
- Object deletion is deliberately scoped to the video’s original key and processed prefix; shared objects are never targeted.
- Signed object/CDN playback remains the significant Phase 4 delivery item and needs separate token/revocation design.
