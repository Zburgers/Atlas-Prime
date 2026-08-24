# 240826-H-version-endpoint

Sector: H — testing, DevEx, and CI
Agent: Luna
Date: 24-08-2026
Branch/Commit: `docs/fullplatform-rollout` / `f3a8464` base, uncommitted changes

## What changed
- Added unauthenticated `GET /version` with exactly `build_sha`, `build_time`, `app_environment`, and `alembic_head` fields.
- Added focused unknown/configured metadata contract tests and a JSON-parsing smoke assertion for the effective Compose build SHA.
- Smoke explicitly exports `ATLAS_BUILD_SHA=unknown` when the process value is unset or empty, so shell precedence matches Compose even when `.env` differs.

## Decisions / ADR notes
- Decision: `alembic_head` is the source-controlled constant `20260824_0019`; update it with future migration heads.
- Reason: the endpoint provides attribution metadata without querying a database or exposing paths, credentials, Clerk/JWT values, or storage keys.
- No ADR-level decision.

## Validation
- `python -m pytest tests/test_health_contract.py -q` from `apps/api`: PASS, 5 tests.
- `python -m pytest -q` from `apps/api`: 144 passed, 5 pre-existing Sector G telemetry-admission failures (`503 TelemetryAdmissionUnavailable` and missing playback events).
- `sh -n scripts/smoke-devex.sh`: PASS.
- `docker compose config -q` and `ATLAS_BUILD_SHA=plan53-parent-check docker compose config -q`: PASS.
- Configured no-secret `/version` probe with `ATLAS_BUILD_SHA=plan53-parent-check ATLAS_BUILD_TIME=2026-08-24T12:00:00Z APP_ENV=staging`: PASS; exact JSON matched the contract.
- Full `make smoke`: Not run; the focused endpoint/runtime probe and Compose checks were run instead.
- `git diff --check`: PASS.

## Files touched
- `apps/api/app/main.py`
- `apps/api/app/schemas/videos.py`
- `apps/api/tests/test_health_contract.py`
- `scripts/smoke-devex.sh`

## Handoff / risks
- Changes remain uncommitted and unpushed; no CI, merge, deployment, or production evidence is claimed.
- Full-suite failures remain outside this task and are caused by unavailable telemetry admission in the local test environment.
- `/version` is attribution metadata only and is not deployment or production proof.
