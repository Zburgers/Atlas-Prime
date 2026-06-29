# 290626-H-wave3-integration-smoke

Sector: H testing, DevEx, and final integration
Agent: Codex
Date: 29-06-2026
Branch/Commit: main / pending local commit

## What changed
- Upgraded `make smoke` from service-health checks to a full upload -> worker -> HLS -> API playback proxy integration smoke.
- Updated the API MVP contract and local-dev docs so smoke coverage no longer claims the D/E path is pending.

## Decisions / ADR notes
- Decision: `make smoke` temporarily enables `ATLAS_ALLOW_DEV_AUTH_HEADERS=true` for local-only integration validation.
- Reason: Wave 3 needs repeatable cross-user upload/playback checks without requiring a live Clerk browser session in CI/local smoke.
- Alternatives considered: Browser-only Clerk smoke, deferred because it is slower and requires external auth state.

## Validation
- `sh -n scripts/smoke-devex.sh`
- `make test` (API 28 passed, worker 2 passed, web node test 1 passed)
- `make lint`
- `make smoke` (ready video `6a94fdb1-5949-4376-82c5-26164bf563b7`; corrupt video `7488ab54-9035-4b4a-a1f1-f8cb833c1bdc` failed with `MEDIA_COMMAND_FAILED`)

## Files touched
- scripts/smoke-devex.sh
- apps/api/app/main.py
- apps/api/tests/test_health_contract.py
- docs/local-dev.md
- memory/290626-H-wave3-integration-smoke.md

## Handoff / risks
- MVP completeness is now validated at the API/worker/storage layer; the remaining owner demo should still manually sign in through Clerk and play a ready private video in the browser at `http://localhost:3001`.
- `make smoke` creates local smoke videos and processed MinIO objects; this is acceptable for dev volumes but not a data cleanup strategy.
- V2 platform suggestions: add direct multipart/resumable uploads with reconciliation, CDN-backed signed delivery, richer creator studio analytics, captions/subtitle workflow, background reprocessing/versioned encodes, search/discovery, comments/reactions, moderation/reporting queues, creator/channel pages, notification feeds, watch history, recommendation experiments, storage lifecycle policies, admin roles, and production observability with metrics/tracing/alerts.
