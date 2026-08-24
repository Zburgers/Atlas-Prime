# 240826-H-build-metadata

Sector: H — testing, DevEx, and CI
Agent: Codex
Date: 24-08-2026
Branch/Commit: `docs/fullplatform-rollout` / `e466aa8` parent, uncommitted changes

## What changed
- Added non-secret `ATLAS_BUILD_SHA` and `ATLAS_BUILD_TIME` build/runtime metadata with exact local default `unknown` for API, web, Compose, and API-based analytics/search services.
- Added API config accessors and focused tests for unknown defaults and environment overrides.

## Decisions / ADR notes
- Decision: keep metadata in ordinary runtime environment variables and Docker build args; do not use `NEXT_PUBLIC_*`, branch names, filesystem discovery, or secrets.
- Reason: Plan 5.3 can import stable accessors while API and web images remain attributable at runtime.
- TDD note: the requested test and implementation were already present in the shared dirty worktree at handoff. The parent `e466aa8` lacks the accessors, but the red phase was not rerun by modifying or resetting that shared worktree.

## Validation
- `python -m pytest apps/api/tests/test_build_metadata.py -q`: PASS, 2 tests.
- `python -m pytest -q` from `apps/api`: 142 passed, 5 pre-existing Sector G telemetry-admission failures caused by unavailable telemetry Redis admission (`503` and missing playback events).
- `ATLAS_BUILD_SHA=plan52-safe-sha ATLAS_BUILD_TIME=2026-08-24T12:00:00Z docker compose config -q`: PASS.
- Explicit metadata lines from `docker compose config`: resolved for API, web, analytics-worker, search-worker, analytics-beat, and web-test build/runtime configuration.
- API image build and web multi-stage runner build with explicit metadata: PASS; `docker run --rm ... env` showed the supplied SHA/time in both final images.
- Metadata source scan found no `NEXT_PUBLIC_*` metadata exposure; `git diff --check`: PASS.

## Files touched
- `.env.example`
- `apps/api/Dockerfile`
- `apps/api/app/core/config.py`
- `apps/api/tests/test_build_metadata.py`
- `apps/web/Dockerfile`
- `compose.yaml`
- `memory/240826-H-build-metadata.md`

## Handoff / risks
- Changes remain uncommitted and unpushed; no CI, deployment, or production evidence is claimed.
- The full API suite still has the five telemetry-admission failures above; they are outside Plan 5.2 and were not changed.
- No media-worker Dockerfile was modified.
