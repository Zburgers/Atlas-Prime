# 050826-ALL-owner-decisions

Sector: ALL
Agent: Codex
Date: 05-08-2026
Branch/Commit: docs/fullplatform-rollout

## What changed
- Recorded operator identity as `ATLAS_ADMIN_CLERK_USER_IDS`.
- Recorded asynchronous deletion status with immediate tombstone and retryable cleanup.
- Recorded telemetry policy: 30-day retention, 120 events/minute/client/video, no persisted IP.
- Selected explicit CI-only Clerk-free smoke mode for release evidence.

## Decisions / ADR notes
- Decision: D-011, D-012, and D-013 are active owner decisions in the engineering handbook.
- Reason: remove agent discretion from cross-cutting auth, deletion, telemetry, and CI behavior.
- Alternatives considered: synchronous deletion, IP-derived identifiers, and CI test Clerk keys were not selected.

## Validation
- `git diff --check` (will be rerun after whitespace normalization).
- Plan index and executable-plan structure checks were previously passing; rerun before push.
- Focused API and web tests passed before this docs-only decision update.

## Files touched
- `docs/PRODUCT_SPEC_AND_ENGINEERING_HANDBOOK.md`
- `docs/plans/README.md`
- `docs/plans/2026-08-04-03-media-publication-deletion.md`
- `docs/plans/2026-08-04-04-telemetry-governance.md`
- `docs/plans/2026-08-04-05-release-evidence.md`
- `docs/architecture/events-and-analytics.md`

## Handoff / risks
- Plan 4 is decision-unblocked but still depends on Plan 3 completion.
- R-001 maximum upload size remains open and must not be inferred by agents.
- CI smoke-mode implementation remains a Plan 5 task; no real Clerk secret is needed for CI mode.
