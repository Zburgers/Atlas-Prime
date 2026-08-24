# 240826-BCDEG-media-publication-deletion

Sector: B/C/D/E/G
Agent: Luna
Date: 24-08-2026
Branch/Commit: docs/fullplatform-rollout / 83229d4 code head; documentation closeout uncommitted

## What changed
- Reconciled API/database, delivery, handbook, plan-index, and operator-runbook documentation with the Plan 3 implementation evidence at `5fb8d86`, `8cf082a`, `a417095`, `88ae38a`, `bb27f28`, and `83229d4`.
- Documented immutable attempt-scoped HLS keys, typed upload inventory, fenced atomic publication, inventory-bound playback, tombstone-first asynchronous deletion, retry/reconciliation behavior, and operator evidence boundaries.
- Resolved C-006, C-007, C-008, and C-009 in the rollout ledger; left C-010, release/deployment evidence, authenticated/browser qualification, and production readiness open.

## Decisions / ADR notes
- Decision: mark Plan 3 `COMPLETE` and Plan 4 `READY` after the parent verified the current code head at `83229d4`.
- Reason: the corrected worker publication path passed the required deterministic tests, lint, alternate-port Compose smoke, and diff checks.
- Alternatives considered: claiming completion from focused tests alone; rejected because local Compose processing must complete the upload-to-playback path.

## Validation
- `make lint` -> PASS: Compose validation, API/worker `compileall`, and web ESLint.
- `make test` -> PASS: 130 API tests, 25 worker tests, and 5 web tests.
- `WEB_PORT=3002 WEB_SMOKE_URL=http://127.0.0.1:3002 make smoke` -> PASS: `ready_video=0eeb78ed-d6f3-481e-96a3-87e2bd13724e`, `bad_video=f1db9f9b-ba61-4bca-869f-2d370fbe1b64`, `failure_code=MEDIA_COMMAND_FAILED`; the ready path reached inventory-bound HLS playback and the failure path remained sanitized.
- `git diff --check` -> PASS.
- Canonical plan index completeness check using `comm -3` with `find` and `awk` -> PASS, no output.
- `make help | rg -n 'processing-recover-stale|deletion-reconcile|make lint|make test|make smoke'` -> PASS; both operator targets present.
- `cd apps/api && python -m app.commands.reconcile_deletions --help` -> PASS.
- `PORT_3001` check -> occupied by an unrelated listener on `127.0.0.1:3001`; it was not stopped.

## Files touched
- `docs/api-database.md`
- `docs/delivery-playback-cdn.md`
- `docs/PRODUCT_SPEC_AND_ENGINEERING_HANDBOOK.md`
- `docs/plans/README.md`
- `docs/runbooks/processing-publication-deletion.md`

## Handoff / risks
- The psycopg cursor-batch remediation is committed at `83229d4`; parent review and the full alternate-port smoke pass are recorded above.
- The plan index records Plan 3 `COMPLETE` and Plan 4 `READY`; no Plan 4 implementation has started.
- Full-stack smoke is local Compose evidence only. Merge, push, deployment, authenticated/browser qualification, and production readiness remain unclaimed. C-010 telemetry governance remains Plan 4 work.
