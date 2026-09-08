# Generated thumbnail set

Sector: D media processing and packaging
Agent: Codex
Date: 15-07-2026
Branch/Commit: docs/fullplatform-rollout

## What changed
- Generated three thumbnails at early, middle, and late media offsets when duration permits.
- Preserved `thumbnail.jpg` as the primary compatibility asset and persisted all generated thumbnails for Studio selection.

## Decisions / ADR notes
- No ADR-level decision.
- Reason: The existing thumbnail manager already supports multiple generated assets; the worker now supplies a useful set.

## Validation
- `docker compose run --rm --build worker pytest tests/test_packager.py tests/test_repository.py -q` (4 passed)

## Files touched
- `workers/media/media_worker/packager.py`
- `workers/media/tests/test_packager.py`

## Handoff / risks
- Very short or unknown-duration media intentionally produces a single thumbnail to avoid invalid seek positions.
