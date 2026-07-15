# Expanded rendition ladder

Sector: D media processing and packaging
Agent: Codex
Date: 15-07-2026
Branch/Commit: docs/fullplatform-rollout

## What changed
- Added 1080p and 480p HLS rendition plans alongside 720p and 360p.
- Kept the source-dimension eligibility filter, so the worker never upscales smaller sources.

## Decisions / ADR notes
- No ADR-level decision.
- Reason: This meets the first Phase 4 media-quality acceptance while preserving the MVP no-upscale invariant.

## Validation
- `docker compose run --rm --build worker pytest tests/test_packager.py -q` (3 passed)

## Files touched
- `workers/media/media_worker/packager.py`
- `workers/media/tests/test_packager.py`

## Handoff / risks
- Per-rendition output metadata and signed/CDN delivery remain later Phase 4 work.
