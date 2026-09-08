# 240826-BCDEG-video-deletion

Sector: B/C/D/E/G
Agent: Luna
Date: 24-08-2026
Branch/Commit: docs/fullplatform-rollout / 88ae38a (working tree uncommitted)

## What changed
- DELETE now locks and tombstones the video in one DB transaction, clears active processing generation, cancels queued/running jobs with `VIDEO_DELETED`, and returns an API-owned 202 body.
- Fresh-session cleanup deletes original and scoped processed storage only after the tombstone commit, finalizes successful tombstones by clearing storage pointers, and preserves failed tombstones with a sanitized retry error.
- Added the operator command `app.commands.reconcile_deletions --apply` and `make deletion-reconcile`; normal user reads, playback, processing status, upload, process, update, and public listing hide tombstoned videos while admin/debug visibility remains available.

## Decisions / ADR notes
- Decision: retain the existing video lifecycle status and use `deleted_at` plus `deletion_status` as the deletion boundary; keep rows, inventory, renditions, thumbnails, and processing-job audit state.
- Reason: tombstone visibility and worker generation fences must commit before any external storage I/O, while retries remain idempotent if objects are already absent.
- Alternatives considered: hard delete, storage cleanup inside the tombstone transaction, a new `deleting` video lifecycle status, or public deletion endpoints.

## Validation
- `docker compose run --rm --build api pytest tests/test_video_deletion.py tests/test_video_api.py::test_deleting_a_video_removes_original_and_processed_storage -q` -> PASS, 8 passed.
- `docker compose run --rm --build api pytest tests/test_storage.py -q` -> PASS, 3 passed.
- `docker compose run --rm --build api pytest -q` -> PASS, 130 passed.
- `docker compose run --rm api python -m compileall -q app tests` and changed-file `ruff check` -> PASS.
- `make help | grep -F 'make deletion-reconcile'`, `python -m app.commands.reconcile_deletions --help`, `sh -n scripts/smoke-devex.sh`, and `git diff --check` -> PASS.

## Files touched
- `apps/api/app/services/videos.py`
- `apps/api/app/api/videos.py`
- `apps/api/app/services/storage.py`
- `apps/api/app/commands/reconcile_deletions.py`
- `Makefile`
- `apps/api/tests/test_video_deletion.py`
- `apps/api/tests/test_video_api.py`

## Handoff / risks
- Existing worker publication fences remain authoritative for finalize-after-tombstone races; no worker, schema, migration, frontend, or serving changes were made in this task.
- Reconciliation processes pending, running, and failed tombstones with fresh sessions and never clears `deleted_at` or restores active generation.
- Full platform smoke, merge, deployment, authenticated browser qualification, and production readiness remain deferred to the parent Plan 3 exit gate.
