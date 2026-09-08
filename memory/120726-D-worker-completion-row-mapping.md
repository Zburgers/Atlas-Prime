# Worker completion row mapping

Sector: D media worker
Agent: Codex
Date: 12-07-2026
Branch/Commit: docs/fullplatform-rollout

## What changed
- Fixed media-worker completion after successful HLS upload when reading the custom-thumbnail existence query.
- Added a repository regression test using the configured dictionary row shape.

## Decisions / ADR notes
- No ADR-level decision.
- Reason: The worker already configures Psycopg `dict_row`, so completion queries must use named fields rather than positional indexes.

## Validation
- `docker compose run --rm --build worker pytest tests/test_repository.py tests/test_packager.py -q` (3 passed)
- `make smoke` (passed; ready-video processing and failure-path checks completed)

## Files touched
- `workers/media/media_worker/repository.py`
- `workers/media/tests/test_repository.py`

## Handoff / risks
- The smoke failure reported during the captions slice was resolved without changing caption, HLS packaging, or database schema behavior.
