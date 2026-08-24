# 240826-D-attempt-scoped-assets

Sector: D
Agent: Luna
Date: 24-08-2026
Branch/Commit: docs/fullplatform-rollout / 5fb8d86 (working tree uncommitted)

## What changed
- Threaded `generation` through HLS packaging and staged every generated asset under `processed/{video_id}/attempts/{generation}/hls/{relative_path}`; legacy `processed/{video_id}/hls/` is untouched.
- Added typed `UploadedHlsAsset` records with storage key, HLS-root-relative path, content type, byte size, and local SHA-256 checksum.
- Made cleanup generation-scoped and idempotent; Celery failure paths log and delete only the matching attempt prefix.

## Decisions / ADR notes
- Decision: keep local HLS output beneath the existing temporary `hls` root and apply the immutable attempt prefix only when deriving object keys.
- Reason: preserves FFmpeg layout and current task payload/API fields while giving Task 3.3 accurate staged keys for publication.
- Alternatives considered: no legacy published-tree cleanup or automatic retry was added.

## Validation
- `docker compose run --rm --build worker pytest tests/test_packager.py -q` -> PASS, 6 passed.
- `docker compose run --rm --build worker pytest tests/test_packager.py tests/test_repository.py -q` -> PASS, 17 passed.
- `ruff check media_worker tests/test_packager.py` -> PASS.
- `docker compose run --rm --build worker python -m compileall -q media_worker tests` -> PASS.
- `git diff --check` -> PASS; exact attempt key strings are asserted in `workers/media/tests/test_packager.py` and confirmed in the worker diff.

## Files touched
- `workers/media/media_worker/packager.py`
- `workers/media/media_worker/storage.py`
- `workers/media/media_worker/celery_app.py`
- `workers/media/tests/test_packager.py`

## Handoff / risks
- Task 3.3 must persist the returned asset inventory and atomically publish the staged `PackageResult` keys; this task does not write inventory rows or switch API publication.
- Task 3.3 remains responsible for stale-generation/deleted-video finalization fencing and post-publication cleanup. Private bucket access and legacy published assets remain unchanged here.
