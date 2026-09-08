# 240826-D-atomic-publication-qa

Sector: D
Agent: Luna
Date: 24-08-2026
Branch/Commit: docs/fullplatform-rollout / bb27f28 base; QA fix uncommitted

## What changed
- Replaced the three direct `Connection.executemany` calls in `MediaRepository.mark_succeeded` with cursor-scoped `executemany` calls inside the existing `conn.transaction()` block.
- Updated the repository fake to expose `cursor()` and `FakeCursor.executemany()` only; the success test asserts that all three publication batches use cursors.

## Decisions / ADR notes
- Decision: use `conn.cursor().executemany(...)` for inventory, rendition, and generated-thumbnail inserts while retaining the existing transaction boundary and `dict_row` connection.
- Reason: psycopg 3 provides `executemany` on cursors, not on `Connection`; the unsupported connection call caused live publication to fail after HLS upload.
- Alternatives considered: individual `Connection.execute` calls; rejected because the cursor batch interface is the supported minimal correction and preserves atomic rollback.

## Validation
- Original smoke failure: worker publication raised `AttributeError: 'Connection' object has no attribute 'executemany'` at `workers/media/media_worker/repository.py:168` after uploading six HLS objects; the attempt cleanup ran and the smoke client received `PROCESSING_FAILED`.
- Red reproduction: `docker compose run --rm --build worker pytest tests/test_repository.py::test_mark_succeeded_supports_the_configured_mapping_row_factory -q` -> FAIL with the same `FakeConnection` `executemany` mismatch after removing the masking fake method.
- `docker compose run --rm --build worker pytest tests/test_repository.py tests/test_packager.py -q` -> PASS, 25 passed in 1.41s.
- `docker compose run --rm --build worker python -m compileall media_worker tests` -> PASS.
- `ruff check workers/media/media_worker workers/media/tests` -> PASS, Ruff 0.15.17.
- `git diff --check` -> PASS.
- Full-stack smoke was not rerun; the parent must independently rerun the alternate-port smoke after review.

## Files touched
- `workers/media/media_worker/repository.py`
- `workers/media/tests/test_repository.py`
- `memory/240826-D-atomic-publication-qa.md`

## Handoff / risks
- Manifest validation, inventory metadata, tombstone/generation fences, custom-thumbnail selection, transaction rollback, and prior-attempt cleanup were not changed.
- The parent should rerun `WEB_PORT=3002 WEB_SMOKE_URL=http://127.0.0.1:3002 make smoke`; this agent does not claim a smoke pass or Plan 3 closeout.
- No commit or push was performed.
