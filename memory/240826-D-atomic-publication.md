# 240826-D-atomic-publication

Sector: D
Agent: Luna
Date: 24-08-2026
Branch/Commit: docs/fullplatform-rollout / 8cf082a (working tree uncommitted)

## What changed
- `MediaRepository.mark_succeeded` now validates the complete attempt manifest before DB work, inserts typed `UploadedHlsAsset` inventory rows, and publishes job, rendition, generated-thumbnail, and video state in one fenced psycopg transaction.
- Added `PublicationResult` with boolean-compatible `applied`, `reason`, and safe `old_generation` output; Celery cleans the current attempt on stale/incomplete finalization and cleans only the prior attempt after commit.
- Tombstone and active-generation predicates are present on the terminal job/video updates; custom selected thumbnails remain selected while generated thumbnails are replaced.

## Decisions / ADR notes
- Decision: derive prior cleanup only from `processed/{video_id}/attempts/{generation}/hls/master.m3u8`; legacy published keys produce no cleanup generation.
- Reason: preserves the old published tree until the transaction commits and makes post-commit cleanup structurally unable to target the legacy prefix or the new generation.
- Alternatives considered: no API publication, serving allowlist, deletion workflow, or automatic retry was added.

## Validation
- `docker compose run --rm --build worker pytest tests/test_repository.py -q` -> PASS, 19 passed.
- `docker compose run --rm --build worker pytest tests/test_packager.py tests/test_repository.py -q` -> PASS, 25 passed.
- `docker compose run --rm --build worker python -m compileall -q media_worker tests` -> PASS.
- `ruff check media_worker tests` -> PASS.
- `git diff --check` -> PASS.

## Files touched
- `workers/media/media_worker/repository.py`
- `workers/media/media_worker/celery_app.py`
- `workers/media/tests/test_repository.py`

## Handoff / risks
- Task 3.4 must bind API playlist, segment, and thumbnail serving to the active generation's `video_asset_inventory`; this task only writes inventory and does not change delivery authorization.
- Full-stack smoke is deferred until Tasks 3.4 and 3.5 complete. Task 3.5 must preserve the tombstone fences and make deletion cleanup/reconciliation account for published and inventoried assets.
- Merge, deployment, authenticated browser qualification, and production readiness are not claimed.
