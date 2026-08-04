# 050826-ALL-contract-boundary-handoff

Sector: A/B/F/G contract boundary
Agent: plan1-task1.6
Date: 05-08-2026
Branch/Commit: docs/fullplatform-rollout (implementation commits bac7a89, fd62a20, d79b42f, ced7472, d33d456)

## What changed
- Reconciled API/database and observability docs with product versus operator response schemas.
- Recorded `ATLAS_ADMIN_CLERK_USER_IDS` as the authoritative operator allowlist and updated C-001/C-002/C-003/C-011/C-012 status evidence.
- Marked Plan 1 complete and Plan 2 ready in the canonical plan index.

## Decisions / ADR notes
- Decision: FastAPI `AdminUserDep` remains authoritative for operator authorization; the Next proxy is transport-only.
- Reason: Preserve one server-side fail-closed authorization boundary while avoiding a second role source.
- Alternatives considered: independent frontend/proxy role checks were not implemented because they cannot replace API enforcement.

## Validation
- `make lint` — PASS (API/worker compile, web lint and production build).
- `make test` — PASS (102 API tests, 5 worker tests, 5 web tests).
- `make smoke` — BLOCKED: existing process/container already owns `127.0.0.1:3001` (`atlas-prime-web-1` bind failure); no source failure observed.
- `git diff --check` — PASS before commit.

## Files touched
- `docs/api-database.md`
- `docs/observability-admin-ops.md`
- `docs/PRODUCT_SPEC_AND_ENGINEERING_HANDBOOK.md`
- `docs/issues.md`
- `docs/plans/README.md`

## Handoff / risks
- C-001 is deliberately partial: API/admin denial is covered, but the proxy does not perform independent role authorization.
- Plan 2 may start only after this handoff commit and its exit-gate evidence are verified; do not infer production readiness from local tests.
