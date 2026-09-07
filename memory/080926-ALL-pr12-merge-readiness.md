# 080926-ALL-pr12-merge-readiness

Sector: ALL / PR #12 merge readiness
Agent: Codex
Date: 08-09-2026
Branch/Commit: docs/fullplatform-rollout / 0415bac5846035f18b4fbfa54c85d11d1e2c4e06

## What changed
- Closed PR #12 P1 blockers for public identity, visibility, durable processing publication, anonymous telemetry, atomic counters, playlist ordering, and release evidence.
- Added the durable processing-dispatch migration/reconciler and shared visibility predicates.
- Reconciled release evidence and the plan ledger to implementation candidate `aee06a58888db8cc4f5536381dfbf4712655ebb0`.
- Marked PR #12 ready for review; no merge or deployment was performed.

## Decisions / ADR notes
- Decision: commit processing job and dispatch intent before broker publication, then reconcile pending publication.
- Reason: closes the send-before-commit race while retaining a retryable path when the broker is unavailable.
- Alternatives considered: direct publish before commit was rejected by the review finding; a separate broker was out of MVP scope.
- Decision: anonymous telemetry identity is a signed server-issued HttpOnly cookie, with the existing 120/minute/client/video limit and 30-day retention.
- Reason: caller-provided UUIDs are not trusted identities and IP persistence is prohibited by the project contract.

## Validation
- `PYTHONPATH=. pytest -q tests` — 152 passed.
- `docker run --rm atlas-prime-worker:latest pytest -q tests` — 25 passed.
- `npm --workspace apps/web test` — 11 passed; web lint and build passed.
- API/worker compileall, `docker compose config -q`, and Alembic `20260908_0020` — passed.
- Exact-SHA local stack smoke at `aee06a58888db8cc4f5536381dfbf4712655ebb0` — passed upload, worker processing, HLS playback, privacy denial, and corrupt-media failure.
- CI run `34169243078` passed at the implementation candidate; final docs-only CI run `34169461787` passed at `0415bac5846035f18b4fbfa54c85d11d1e2c4e06`.

## Files touched
- `apps/api/app/domain/visibility.py`
- `apps/api/app/services/processing_dispatch.py`
- `apps/api/app/services/analytics.py`
- `apps/api/app/services/telemetry_admission.py`
- `apps/api/alembic/versions/20260908_0020_durable_processing_dispatch.py`
- `docs/audits/release-evidence-current.md`
- `docs/plans/README.md`

## Handoff / risks
- Final handoff must verify the pushed head and CI again after this memory-only commit; current PR state before this commit was ready, open, mergeable, and clean.
- Resolved issues closed: #1, #3-#10, #13, #20, #21, and #23. Open follow-ups remain #2, #14-#19, #22, and #24.
- P2 comments on analytics rebuild query bounding and container-startup migration were explicitly deferred. Merge, deployment, authenticated browser qualification, and production qualification remain unverified.
