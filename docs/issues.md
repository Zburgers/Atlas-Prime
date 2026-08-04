# Atlas Prime Issue Tracker

This tracker records unresolved repository findings without replacing GitHub issues or the handbook. Search finding IDs before adding an entry. Resolve an item only with an attributable implementation and validation commit.

--

ID: DOC-001
Status: RESOLVED IN DOCS
Severity: High
Finding: The rollout had no complete plan index, its live “next step” named already-delivered Issue 9, and broad phase allocations required agents to invent sequencing, files, and gates.
Evidence: `docs/plans/02-fullplatform-vision.md` on pre-reconciliation commit `65e23a0`; delivered history through `4f0e98d`.
Resolution: `docs/plans/README.md` now inventories every plan and orders five gated sequential remediation plans. Runtime implementation remains pending under those plans.

--

ID: CI-001
Status: OPEN
Severity: Medium
Finding: PR #11 CI run `30856956679` passed API/web tests but failed smoke because the web container had no Clerk publishable key and never became healthy.
Scope: Plan 5, Task 5.1.
Risk: Current-head release evidence is not green or self-contained.

--

ID: C-001
Status: PARTIAL — API boundary resolved; proxy remains transport-only
Severity: High
Finding: Operator authorization must be enforced server-side and not inferred from frontend access.
Evidence: `AdminUserDep` and `ATLAS_ADMIN_CLERK_USER_IDS`; API denial regression tests at `bac7a89`. Next proxy forwards credentials and relies on FastAPI, so no independent proxy role gate is claimed.
Scope: Preserve backend fail-closed authorization; proxy/UI hardening requires a separately indexed task if owner requires duplicate enforcement.

--

ID: C-002
Status: RESOLVED ON ROLLOUT BRANCH
Severity: High
Finding: Unlisted videos must remain direct-link readable without appearing in global discovery.
Evidence: API regression tests at `bac7a89` cover anonymous and non-owner lists plus direct read/playback; implementation filters non-owner listings to public ready videos.
Scope: Keep regression coverage in future route changes.

--

ID: C-003
Status: RESOLVED ON ROLLOUT BRANCH
Severity: Medium
Finding: Product responses must not expose storage keys or Celery task identifiers.
Evidence: Product/operator schema split at `fd62a20`; frontend caller and smoke coverage at `d79b42f`.
Scope: Keep internal fields restricted to protected operator/debug schemas.

--

ID: C-004,C-005,C-006,C-007,C-008,C-009,C-010
Status: OPEN OR PARTIAL
Severity: Medium to High
Finding: Remaining upload/job generation, atomic publication/deletion, segment inventory, and telemetry governance issues.
Evidence: `docs/PRODUCT_SPEC_AND_ENGINEERING_HANDBOOK.md` reconciliation addendum.
Scope: Indexed Plans 2-4; do not implement out of order.

--

ID: C-011
Status: RESOLVED ON ROLLOUT BRANCH
Severity: High
Finding: Configured Clerk authorized-party allowlists must reject missing or mismatched `azp` claims.
Evidence: Fail-closed verification and tests at `ced7472`.
Scope: Preserve strict behavior when `CLERK_AUTHORIZED_PARTIES` is non-empty.

--

ID: C-012
Status: RESOLVED ON ROLLOUT BRANCH
Severity: Medium
Finding: Watch UI must not expose sector/process-internal ownership language.
Evidence: User-safe status guidance and smoke assertions at `d33d456`.
Scope: Keep copy user-safe as lifecycle states evolve.

--

ID: DEP-001
Status: OPEN
Severity: Needs triage
Finding: The current web image build reported six npm audit findings (two low, four high) after `npm ci`. No package-level exploitability review was performed in this docs reconciliation.
Evidence: 2026-08-04 `docker compose run --rm --build web-test npm --workspace apps/web test` build output.
Scope: Dependency audit/fix requires a separately reviewed change; do not run an unbounded forced upgrade inside Plans 1-5.

--
