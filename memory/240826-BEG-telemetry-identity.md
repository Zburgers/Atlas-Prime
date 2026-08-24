# 240826-BEG-telemetry-identity

Sector: B/E/G
Agent: Luna
Date: 24-08-2026
Branch/Commit: docs/fullplatform-rollout / 0bde683 base; Plan 4.1 uncommitted

## What changed
- Added required UUID `playback_session_id` and `event_id` fields to the playback event request, ORM model, and response; `event_id` is unique.
- Added migration `20260824_0019` with nullable add, deterministic Python UUID5 backfill for historical rows, final not-null enforcement, and SQLite batch-mode unique constraint support.
- Made event retries idempotent: same-video duplicates return the existing row with HTTP 200 before history/counter side effects; cross-video reuse returns sanitized HTTP 409 after the requested-video access check.
- Updated directly required telemetry fixture posts and added identity/idempotency/conflict/schema tests.

## Decisions / ADR notes
- Decision: use client-supplied UUIDs as the event identity contract and generate deterministic UUID5 values from historical primary keys during migration.
- Reason: event retries need a durable unique key, while historical rows need portable, repeatable values without PostgreSQL-only random functions or IP-derived data.
- Alternatives considered: accepting missing IDs and generating them in the API; rejected because Plan 4.2 must establish stable client retry identity and newly accepted payloads should carry both identifiers.

## Validation
- `docker compose run --rm --build api pytest tests/test_analytics_events.py -q` -> PASS, 7 passed in 2.30s.
- `docker compose run --rm --build api pytest tests/test_video_api.py tests/test_subscriptions_history.py tests/test_recommendation_logging.py -q` -> PASS, 47 passed in 7.94s.
- `docker compose run --rm --build api alembic upgrade head` -> PASS, PostgreSQL `20260824_0018 -> 20260824_0019`.
- SQLite migration smoke probe with a historical row -> initial assertion failed because SQLite reflects the named unique constraint through `get_unique_constraints()` rather than `get_indexes()`; corrected probe passed with deterministic backfill, NOT NULL columns, and named unique `event_id` constraint.
- `docker compose run --rm --build api python -m compileall -q app/db/models.py app/schemas/videos.py app/api/videos.py alembic/versions/20260824_0019_telemetry_governance.py tests/test_analytics_events.py tests/test_video_api.py tests/test_subscriptions_history.py tests/test_recommendation_logging.py` -> PASS.
- `ruff check apps/api/app/db/models.py apps/api/app/schemas/videos.py apps/api/app/api/videos.py apps/api/alembic/versions/20260824_0019_telemetry_governance.py apps/api/tests/test_analytics_events.py apps/api/tests/test_video_api.py apps/api/tests/test_subscriptions_history.py apps/api/tests/test_recommendation_logging.py` -> PASS, Ruff 0.15.17.
- `git diff --check` -> PASS.
- Full-stack smoke and Plan 4 completion were not run or claimed.

## Files touched
- `apps/api/alembic/versions/20260824_0019_telemetry_governance.py`
- `apps/api/app/db/models.py`
- `apps/api/app/schemas/videos.py`
- `apps/api/app/api/videos.py`
- `apps/api/tests/test_analytics_events.py`
- `apps/api/tests/test_video_api.py`
- `apps/api/tests/test_subscriptions_history.py`
- `apps/api/tests/test_recommendation_logging.py`
- `memory/240826-BEG-telemetry-identity.md`

## Handoff / risks
- Plan 4.2 must generate one session UUID per watch load and one event UUID per emitted event, reusing the event UUID across retries; current backend validation requires both fields.
- Rate limiting, retention, aggregate/admin telemetry, frontend generation, and full-stack qualification remain later Plan 4 tasks.
- Access is checked before duplicate lookup; cross-video event IDs do not disclose the existing row. No raw IP or derived identifier is persisted or logged.
- No commit or push was performed.
