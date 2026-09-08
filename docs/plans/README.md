# Atlas Prime Plan Index And Rollout Ledger

Status: **canonical execution index**
Last reconciled: 2026-09-08
Repository branch: `main`
Current main baseline: `50e3f325c5e07376c4b703312d3f422d7ecd572c` (PR #12 merge commit)
PR #12 final runtime/test candidate: `a64364ab84708303f356eb74130e7d249ffaf970`
PR #12 final docs head: `378c5f2bcb02cec77365dae169dd29dbee3bfe23`
PR #12 final exact-head CI: `34223945178` — passed

## Contract

This file is the **only live execution index**. Phase headings in the handbook, GitHub Issues, research notes, old "next step" paragraphs, and the full-platform vision are context; they are not agent queues.

Execution is sequential unless this index or the selected executable plan explicitly says otherwise. An agent must verify the current `main` SHA and the selected plan's entry gate before coding. Historical green evidence must never be inherited as proof for a changed head.

Precedence for implementation work:

1. `docs/00-ground-truth-mvp-spec.md` — approved MVP boundaries and locked contracts.
2. `docs/PRODUCT_SPEC_AND_ENGINEERING_HANDBOOK.md` — implementation evidence and hardening findings.
3. This index — current plan state and execution order.
4. The selected executable plan below.
5. Sector manifests and architecture docs for narrow interfaces.
6. Code, migrations, tests, current GitHub Issues, and runtime evidence — final descriptive truth.

## Plan Inventory

| Order | Plan | Kind | State | Entry gate | Exit evidence |
|---:|---|---|---|---|---|
| I | `README.md` | Canonical index | ACTIVE | None | Index completeness check |
| R0 | `290626-post-mvp-brainstorm.md` | Research input | REFERENCE ONLY | None | Never executable |
| R1 | `02-fullplatform-vision.md` | Architecture/rollout umbrella | ACTIVE REFERENCE | Read after MVP contracts | Never used as a task queue |
| 1 | `2026-08-04-01-contract-boundary.md` | Executable remediation | COMPLETE | Historical gate | Evidence retained in plan/release audit |
| 2 | `2026-08-04-02-upload-job-idempotency.md` | Executable remediation | COMPLETE | Plan 1 complete | Evidence retained in plan/release audit |
| 3 | `2026-08-04-03-media-publication-deletion.md` | Executable remediation | COMPLETE | Plan 2 complete | Evidence retained in plan/release audit |
| 4 | `2026-08-04-04-telemetry-governance.md` | Executable remediation | COMPLETE | Plan 3 complete; D-013 approved | PR #12 runtime candidate `a64364a`, CI `34223397162` |
| 5 | `2026-08-04-05-release-evidence.md` | Executable release gate | COMPLETE | Plans 1–4 complete | PR #12 docs head `378c5f2`, CI `34223945178`; merged as `50e3f325` |
| 6 | `2026-09-08-06-post-merge-stabilization.md` | Executable stabilization roadmap | READY | PR #12 merged to `main` as `50e3f325`; Plans 1–5 complete | Per-slice exact-head CI/gate + Plan 6 final whole-stack gate |

Every new file under `docs/plans/` must appear in this table before it can become executable.

## Current execution state

PR #12 is merged. The rollout branch is no longer the execution branch.

The next approved executable work is:

**Plan 6 — Post-Merge Stabilization**

Scope is deliberately bounded to:

1. #2 — server-side web/admin authorization;
2. #19 — decoded-media complexity, beginning with a bounded research spike because numeric media limits are not owner-approved;
3. #24 — nonblocking streamed HLS proxy;
4. #22 — bounded/isolated deep readiness;
5. #18 — durable cleanup of superseded original uploads.

Plan 6 defines one coherent PR per implementation slice. Do not combine these into another broad rollout branch.

The #19 research protocol is:

`docs/research/2026-09-08-media-complexity-admission-spike.md`

The research task may propose D-014, but **implementation is blocked until the owner explicitly approves D-014**. The spike does not authorize numeric media limits.

## Post-PR #12 reconciled state

PR #12 merged on 2026-09-08 as:

`50e3f325c5e07376c4b703312d3f422d7ecd572c`

Qualified inputs:

- runtime/test candidate `a64364ab84708303f356eb74130e7d249ffaf970`;
- runtime CI `34223397162` — Compose, API, web, full Sector H smoke passed;
- docs-inclusive PR head `378c5f2bcb02cec77365dae169dd29dbee3bfe23`;
- exact-head CI `34223945178` — passed;
- blocking PR review threads resolved before merge.

Resolved/closed by that rollout reconciliation:

- #1
- #3–#10
- #13
- #20
- #21
- #23

Open work intentionally carried forward:

- #2
- #14–#19
- #22
- #24
- nonblocking analytics rebuild scalability
- migration-at-container-startup orchestration

Only #2, #19, #24, #22, and #18 are promoted into Plan 6. The rest stay backlog/reference until explicitly promoted.

## Owner decisions

### D-011 — operator identity

`ATLAS_ADMIN_CLERK_USER_IDS` is the operator/admin identity source.

Plan 6 #2 must reuse this source in the web server boundary. It must not introduce Clerk Organizations, custom role storage, or a second admin source. FastAPI remains authoritative even after the web adds defense in depth.

### D-012 — video deletion

Deletion uses immediate tombstone + asynchronous retryable cleanup.

Plan 6 #18 should reuse this durability philosophy for superseded-original cleanup without changing the canonical whole-video deletion contract.

### D-013 — telemetry

- raw playback-event retention: 30 days;
- admission: 120 events/minute/client/video;
- persist no raw IP or derived IP identifier.

Current implementation uses verified-user or signed-anonymous per-client buckets plus a separate short-lived new-anonymous-identity circuit breaker. Plan 6 must not change this contract.

### R-001 — upload byte maximum

**Still unresolved.**

The local configuration currently has an upload-byte default, but agents must not turn that implementation default into a new owner policy or silently change the maximum.

### D-014 — decoded-media processing envelope

**NOT YET DECIDED.**

Plan 6 task 6.2 is a bounded research spike whose only purpose is to produce measured candidate envelopes. Task 6.6 may implement #19 only after the owner explicitly approves D-014.

D-014 must decide at least:

- max duration;
- max effective dimensions/pixel area;
- max frame rate;
- optional derived decoded-work ceiling;
- missing/non-finite metadata behavior;
- rotation/fps precedence;
- whether Compose worker CPU/memory caps are part of the same remediation.

## Shipyard execution discipline for Plan 6

Plan 6 adopts the following Shipyard properties:

- roadmap work is split into **PR-sized child tasks**;
- each child task is specced against a recorded current commit;
- each spec records the chosen approach and strongest rejected alternative;
- ordered implementation changes name current file anchors;
- activated risks have verification obligations: a claim plus named evidence;
- a bounded spike is used only when a decision genuinely needs data;
- shipping starts from fresh `main`;
- PR head, CI-green commit, and independently reviewed/gated commit must converge to the same SHA;
- a post-review code change invalidates the old gate;
- the implementation stops before merge unless the owner directly authorizes merge.

Atlas's repository contract remains authoritative where it is stricter.

## Sequential Agent Protocol

For each Plan 6 child:

1. Fetch current `origin/main`.
2. Record base SHA and verify the issue premise still exists.
3. Read:
   - `docs/00-ground-truth-mvp-spec.md`;
   - `docs/01-agent-operating-contract.md`;
   - `docs/plans/README.md`;
   - `docs/plans/2026-09-08-06-post-merge-stabilization.md`;
   - named sector manifests;
   - recent relevant memory;
   - latest official docs.
4. Confirm one PR-sized spec. If the base materially drifted, re-spec rather than blindly executing this file.
5. Run red-test → minimal implementation → focused green.
6. Run the child verification obligations.
7. Run whole-stack gates required by the plan.
8. Add exactly one relevant memory handoff.
9. Push and wait for exact-head CI.
10. Independent review/gate the exact head.
11. Close the issue only when that exact implementation is evidenced.
12. Stop before merge unless directly authorized by the owner.

Minor path drift may be corrected and recorded. A schema/interface redesign, missing owner ruling, failed entry gate, or architecture mismatch is a stop condition.

## Explicitly not executable

There is deliberately no approved implementation plan here for:

- Recommendation V2 / ML personalization;
- monetization/payments;
- live streaming;
- native mobile;
- production deployment/qualification;
- #14–#17 media-output correctness;
- analytics rebuild scalability;
- migration orchestration.

Those remain backlog/reference until the owner promotes them into a stamped executable plan.

## Index Completeness Check

Repeatable check:

```sh
comm -3 \
  <(find docs/plans -maxdepth 1 -type f -name '*.md' -printf '%f\n' | sort) \
  <(awk -F'`' '/^\|/{if ($2 ~ /\.md$/) print $2}' docs/plans/README.md | sort -u)
```

Expected: no output.

## Historical evidence

Detailed Plan 1–5 command output, commit attribution, and release qualification are preserved in:

- the individual `docs/plans/2026-08-04-0*.md` files;
- `docs/audits/release-evidence-current.md`;
- PR #12 discussion/review history.

This index intentionally carries only the current execution authority plus enough historical attribution to avoid inheriting stale green claims.
