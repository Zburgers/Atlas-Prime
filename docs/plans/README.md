# Atlas Prime Plan Index And Rollout Ledger

Status: canonical plan index
Last reconciled: 2026-08-04
Repository branch: `docs/fullplatform-rollout`
Reconciliation base commit: `65e23a0697091916f84b4b3b64953372730c7998`
Merged handbook PR: [#11](https://github.com/Zburgers/Atlas-Prime/pull/11), merge commit `8d0ebc5f7c08d66c2d5edbe910c1aee740bed9b3`

## Contract

This file is the only live execution index. Phase headings in the handbook and full-platform vision describe intent; they are not agent queues. Agents must not select work from an unindexed phase, brainstorm, issue list, or old “next step” paragraph.

Execution is sequential unless this index explicitly says otherwise. A later plan may start only when the prior plan's exit gate is recorded as passed at an attributable commit. The next agent must verify the entry gate rather than inherit a historical green claim.

Precedence for implementation work:

1. `docs/00-ground-truth-mvp-spec.md` — approved MVP boundaries and locked contracts.
2. `docs/PRODUCT_SPEC_AND_ENGINEERING_HANDBOOK.md` — implementation evidence and hardening findings, with the rollout-branch addendum.
3. This index — current plan state and execution order.
4. The selected executable plan below.
5. Sector manifests and architecture docs for narrow interfaces.
6. Code, migrations, tests, and runtime evidence — final descriptive truth.

## Plan Inventory

| Order | Plan | Kind | State | Entry gate | Exit evidence |
|---:|---|---|---|---|---|
| I | `README.md` | Canonical index | ACTIVE | None | Index completeness check |
| R0 | `290626-post-mvp-brainstorm.md` | Research input | REFERENCE ONLY | None | Never executable |
| R1 | `02-fullplatform-vision.md` | Architecture/rollout umbrella | ACTIVE REFERENCE | Read after MVP contracts | Never used as a task queue |
| 1 | `2026-08-04-01-contract-boundary.md` | Executable remediation | READY | Current branch includes PR #11 and post-MVP rollout | Focused auth/API/web tests plus always-green gate |
| 2 | `2026-08-04-02-upload-job-idempotency.md` | Executable remediation | BLOCKED BY 1 | Plan 1 exit recorded | Concurrency/redelivery/recovery tests |
| 3 | `2026-08-04-03-media-publication-deletion.md` | Executable remediation | BLOCKED BY 2 | Generation/attempt contract merged | Publication/deletion race suite plus smoke |
| 4 | `2026-08-04-04-telemetry-governance.md` | Executable remediation | BLOCKED BY 3 | R-004 accepted on 2026-08-05; Plan 3 exit still required | Rate, dedupe, retention, privacy tests |
| 5 | `2026-08-04-05-release-evidence.md` | Executable release gate | BLOCKED BY 4 | Plans 1-4 complete | Green CI/current-head gates at one SHA |

There is deliberately no implementation plan for ML personalization, monetization, live streaming, native mobile, or production deployment. Those remain unapproved or premature under the MVP contract. Creating detailed build instructions for them would give agents false authority and recreate the non-determinism this index prevents.

## Reconciled Rollout State

The PR #11 handbook audited `main` at `dcf8d5cd3d18bb29dccb70dbce44405043a8adcb`. This rollout branch contains substantial later implementation. Findings therefore reconcile as follows:

| Handbook item | Rollout-branch state | Current action |
|---|---|---|
| C-001 admin authorization | PARTIALLY RESOLVED | API uses `AdminUserDep` and `ATLAS_ADMIN_CLERK_USER_IDS`; Plan 1 verifies API/proxy/UI boundaries |
| C-002 unlisted discovery | RESOLVED | Global listing filters to `public`; Plan 1 preserves regression tests |
| C-003 response internals | OPEN | Plan 1 removes storage keys and Celery task IDs from normal responses |
| C-004 upload race/idempotency | OPEN | Plan 2 |
| C-005 processing attempt ownership | PARTIALLY RESOLVED | Atomic queued claim exists; lease/generation/finalization fencing remains in Plan 2 |
| C-006 partial HLS cleanup | PARTIALLY RESOLVED | Failure cleanup exists; attempt-scoped atomic publication remains in Plan 3 |
| C-007 storage deletion | PARTIALLY RESOLVED | Object cleanup exists; asynchronous tombstone/retry workflow remains in Plan 3 |
| C-008 active-worker deletion fence | OPEN | Plan 3 |
| C-009 segment inventory binding | OPEN | Plan 3 |
| C-010 telemetry governance | OPEN | Plan 4 after Plan 3; R-004 policy is recorded |
| C-011 strict Clerk `azp` | OPEN | Plan 1 |
| C-012 stale watch copy | OPEN | Plan 1 |
| Current-head/release evidence | OPEN | Plan 5; PR #11 CI failed on missing Clerk publishable key |

Post-MVP product slices present on this branch include public discovery, channels, likes, watch later, Studio, comments, deterministic feeds, recommendation logging, thumbnails, moderation, analytics, captions, subscriptions, history, playlists, rich playback events, expanded media output, chapters, signed redirect delivery, Meilisearch indexing/read fallback, accessibility verification, and caption transcript search.

## Owner decisions recorded 2026-08-05

- D-011: keep `ATLAS_ADMIN_CLERK_USER_IDS` as the operator identity source.
- D-012: use asynchronous deletion status with an immediate tombstone and retryable cleanup.
- D-013: retain telemetry 30 days, cap admission at 120 events/minute/client/video, and persist no IP.
- CI release evidence will use an explicit Clerk-free smoke mode in CI; production and normal local auth remain Clerk-backed.
- R-001 (maximum upload size) remains open; agents must not infer a new limit.

These slices do not bypass the remediation sequence. Hardening Plans 1-5 are the active queue. Recommendation V2 and ML remain deferred until the release-evidence gate passes and the owner explicitly promotes that scope.

## Sequential Agent Protocol

For each plan:

1. Verify branch, commit, clean/dirty state, and the plan entry gate.
2. Read the required project documents and only the sector manifests named by the plan.
3. Execute tasks strictly by numeric ID; do not parallelize tasks that share schema, status, storage, or response contracts.
4. Use red-test → minimal implementation → focused green-test per task.
5. Run the plan exit gate and the required whole-stack gate.
6. Create exactly one new `memory/DDMMYY-SECTOR-short-topic.md` for that agent handoff.
7. Update this ledger's state and evidence commit. Never silently reorder or broaden a plan.

Minor path drift may be corrected and recorded in the handoff. A schema/interface redesign, missing ruling, failed entry gate, or architecture mismatch is a stop condition: update the plan and obtain owner approval before implementation continues.

## Index Completeness Check

Every markdown file currently under `docs/plans/` appears in the inventory above. Validation must fail if a future plan is added without an inventory row.

Repeatable check:

```sh
comm -3 \
  <(find docs/plans -maxdepth 1 -type f -name '*.md' -printf '%f\n' | sort) \
  <(awk -F'`' '/^\|/{if ($2 ~ /\.md$/) print $2}' docs/plans/README.md | sort -u)
```

Expected: no output.
