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

ID: C-003,C-004,C-005,C-006,C-007,C-008,C-009,C-010,C-011,C-012
Status: OPEN OR PARTIAL
Severity: Medium to High
Finding: Remaining response-boundary, upload/job generation, atomic publication/deletion, segment inventory, telemetry governance, strict Clerk `azp`, and stale UI issues.
Evidence: `docs/PRODUCT_SPEC_AND_ENGINEERING_HANDBOOK.md` reconciliation addendum.
Scope: Indexed Plans 1-4; do not implement out of order.

--

ID: DEP-001
Status: OPEN
Severity: Needs triage
Finding: The current web image build reported six npm audit findings (two low, four high) after `npm ci`. No package-level exploitability review was performed in this docs reconciliation.
Evidence: 2026-08-04 `docker compose run --rm --build web-test npm --workspace apps/web test` build output.
Scope: Dependency audit/fix requires a separately reviewed change; do not run an unbounded forced upgrade inside Plans 1-5.

--
