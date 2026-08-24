# 240826-BEG-telemetry-retention

Sector: B/E/G
Agent: Luna
Date: 24-08-2026
Branch/Commit: docs/fullplatform-rollout / ef8b711 base; Plan 4.4 uncommitted

## What changed
- Added 30-day raw `playback_events` retention with a strict UTC cutoff: only `created_at < now_utc - 30 days` is eligible; exact-cutoff rows remain.
- Added dry-run-by-default `purge_telemetry` command with sanitized aggregate JSON and bounded `--batch-size`; `--apply` is required for deletion.
- Added one 00:20 UTC Celery Beat purge task on the existing analytics queue after the 00:05 rebuild schedule.

## Decisions / ADR notes
- Decision: select only bounded primary-key batches, delete by those IDs with the strict cutoff predicate, and commit each batch using the injected `AsyncSession`.
- Reason: this avoids loading event payloads into Python, works across PostgreSQL and SQLite test schemas, preserves foreign-key behavior, and makes reruns idempotent.
- Logs and command output contain only status, cutoff, batch size, eligible count, purged count, and batch count; no client or row identifiers are emitted.

## Validation
- `docker compose run --rm --build api pytest tests/test_telemetry_retention.py tests/test_analytics_worker.py -q` -> PASS, 8 passed in 1.40s.
- `docker compose run --rm --build api pytest tests/test_analytics_events.py -q` -> PASS, 10 passed in 3.76s.
- `docker compose run --rm --build api python -m compileall -q app/services/telemetry_retention.py app/commands/purge_telemetry.py app/worker/analytics.py tests/test_telemetry_retention.py tests/test_analytics_worker.py` -> PASS.
- `ruff check apps/api/app/services/telemetry_retention.py apps/api/app/commands/purge_telemetry.py apps/api/app/worker/analytics.py apps/api/tests/test_telemetry_retention.py apps/api/tests/test_analytics_worker.py` -> PASS.
- `make help` -> PASS; `telemetry-purge` listed as dry-run by default.
- `docker compose run --rm api python -m app.commands.purge_telemetry --help` -> PASS; `--apply` and bounded `--batch-size` documented.
- `git diff --check` -> PASS.
- No full-stack smoke, Plan 4 completion, commit, or push was performed.

## Files touched
- `apps/api/app/services/telemetry_retention.py`
- `apps/api/app/commands/purge_telemetry.py`
- `apps/api/app/worker/analytics.py`
- `apps/api/tests/test_telemetry_retention.py`
- `apps/api/tests/test_analytics_worker.py`
- `Makefile`
- `memory/240826-BEG-telemetry-retention.md`

## Handoff / risks
- Scheduled purge applies retention at 00:20 UTC through the existing analytics worker/beat process; no second scheduler was introduced.
- A failure during apply rolls back the current batch and propagates to the command/task; already committed prior batches remain safely purged and a rerun is idempotent.
- Admin telemetry health, retention observability beyond aggregate logs, full-stack qualification, and Plan 4 completion remain later work.
