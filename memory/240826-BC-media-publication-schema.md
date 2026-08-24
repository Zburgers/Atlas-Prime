# 240826-BC-media-publication-schema

Sector: B/C
Agent: Luna
Date: 24-08-2026
Branch/Commit: docs/fullplatform-rollout / 9ad82bb (working tree uncommitted)

## What changed
- Added `videos.deleted_at`, `videos.deletion_status`, and `videos.deletion_error`; deletion status is `pending`, `running`, `failed`, or `complete`, with `complete` as the non-null ORM/server default for existing and new non-tombstoned videos.
- Added `video_asset_inventory` with UUID identity, generation/path uniqueness, FK cascade to `videos`, content metadata, nonnegative byte size, SHA-256 text, and created time.
- Added migration `20260824_0018` from `20260805_0017`; no video lifecycle status, API response, or storage layout changed.

## Decisions / ADR notes
- Decision: keep deletion state separate from `VideoStatus`, and enforce only per-video/per-generation/path uniqueness in this table.
- Reason: deletion is a tombstone concern, while the canonical video lifecycle remains unchanged; PostgreSQL constraints cannot inspect `videos.active_processing_generation` across tables.
- Alternatives considered: no cross-table partial unique index was attempted.

## Validation
- `docker compose run --rm --build api alembic upgrade head` -> PASS; upgraded `20260805_0017` to `20260824_0018`.
- `docker compose run --rm --build api pytest tests/test_media_publication_schema.py -q` -> PASS, 4 passed.
- `docker compose run --rm --build api pytest tests/test_video_status.py tests/test_video_api.py -q` -> PASS, 37 passed.
- `docker compose run --rm api alembic downgrade 20260805_0017 && docker compose run --rm api alembic upgrade head` -> PASS; reversible rollback/re-upgrade exercised.
- `docker compose run --rm api alembic heads` -> PASS; exactly one head, `20260824_0018`.
- PostgreSQL catalog inspection -> PASS; `timestamptz`/nullable deletion timestamp, `complete` default, named deletion check, FK `CASCADE`, unique identity, and lookup indexes confirmed.
- `python -m compileall -q apps/api/app apps/api/tests/test_media_publication_schema.py` and `git diff --check` -> PASS.

## Files touched
- `apps/api/alembic/versions/20260824_0018_media_publication_deletion.py`
- `apps/api/app/db/models.py`
- `apps/api/app/domain/status.py`
- `apps/api/tests/test_media_publication_schema.py`

## Handoff / risks
- Plan 3.2-3.5 must consume these fields: attempt-scoped inventory writes, atomic publication, inventoried delivery, and tombstone cleanup/reconciliation.
- `relative_path` is an opaque path relative to the published HLS root; no absolute filesystem path or object-layout behavior is exposed by this task.
- Inventory rows are intended to be append-only; later worker/repository code must preserve the SHA-256 and generation/path identity rather than updating published assets.
- Merge, deployment, authenticated browser qualification, and production readiness are not claimed.
