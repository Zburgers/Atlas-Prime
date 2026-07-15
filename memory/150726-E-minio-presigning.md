# 150726-E-minio-presigning

Sector: E delivery
Agent: Codex
Date: 15-07-2026
Branch/Commit: docs/fullplatform-rollout (pending commit)

## What changed
- Added processed-object presigning to the MinIO storage abstraction.
- Added a focused regression test for bounded object key and expiry forwarding.

## Decisions / ADR notes
- No ADR-level decision.

## Validation
- `docker compose run --rm --build api pytest tests/test_storage.py -q` (3 passed)

## Files touched
- apps/api/app/services/storage.py
- apps/api/tests/test_storage.py

## Handoff / risks
- Manifest delivery must validate asset paths before calling this method; presigning alone is not an authorization boundary.
