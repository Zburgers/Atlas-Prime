# 150726-ABG-processing-timeline

Sector: A/B/G Studio, API, and operations visibility
Agent: Codex
Date: 15-07-2026
Branch/Commit: docs/fullplatform-rollout (pending commit)

## What changed
- Added an owner-only processing-history endpoint that returns every job attempt in creation order.
- Added an accessible Studio processing timeline that shows each durable worker stage, attempt, timestamp, and sanitized failure message.

## Decisions / ADR notes
- Decision: Reuse `video_processing_jobs` as the creator timeline source instead of introducing a parallel event table.
- Reason: Job attempts and durable stages already capture the actionable lifecycle without duplicating operational data.

## Validation
- Test-first API contract: verified the timeline endpoint was absent before implementation.
- `make lint` (passed)
- `make test` (passed)
- `make smoke` (passed: ready video and corrupt-media failure path)

## Files touched
- apps/api/app/services/studio.py
- apps/api/app/api/studio.py
- apps/api/app/schemas/videos.py
- apps/web/app/studio/videos/[videoId]/processing-timeline.tsx
- apps/api/tests/test_studio.py

## Handoff / risks
- The Studio timeline is owner-only and ordered chronologically; admin debugging remains a separate operator surface.
- Storage lifecycle retention and signed object/CDN delivery remain the next substantive Phase 4 items.
