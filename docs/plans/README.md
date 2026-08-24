# Atlas Prime Plan Index And Rollout Ledger

Status: canonical plan index
Last reconciled: 2026-08-24
Repository branch: `docs/fullplatform-rollout`
Reconciliation base commit: `3021889` (parent-verified Plan 4 closeout evidence)
Current release-evidence candidate: `8e9b3244e9e47c488b1a5de4d4cbc9f10ef36187`
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
| 1 | `2026-08-04-01-contract-boundary.md` | Executable remediation | COMPLETE | Exit evidence recorded at `5a44489` (make lint/test pass; smoke blocked only by occupied 127.0.0.1:3001) | `bac7a89`, `fd62a20`, `d79b42f`, `ced7472`, `d33d456`, `5a44489` |
| 2 | `2026-08-04-02-upload-job-idempotency.md` | Executable remediation | COMPLETE | Plan 1 exit recorded; generation contract and bounded recovery validated at `6bb8064` | `6bb8064`: `make test` (115 API, 14 worker, 5 web); `make lint`; alternate-port smoke passed |
| 3 | `2026-08-04-03-media-publication-deletion.md` | Executable remediation | COMPLETE | Plan 2 COMPLETE at `6bb8064`; Plan 3 implementation and exit evidence are verified at `83229d4` | `83229d4`: publication/deletion tests, `make lint`, `make test`, alternate-port smoke, and `git diff --check` |
| 4 | `2026-08-04-04-telemetry-governance.md` | Executable remediation | COMPLETE | Plan 3 COMPLETE at `83229d4`; R-004 accepted on 2026-08-05; parent verified the Plan 4 exit gate at `3021889` | `3021889`: `make lint`, `make test` (145 API, 25 worker, 9 web), alternate-port smoke, `git diff --check`, and local/browser accessibility evidence |
| 5 | `2026-08-04-05-release-evidence.md` | Executable release gate | COMPLETE | Plans 1-4 complete; Plan 4 exit evidence is recorded at `3021889` | Candidate `8e9b3244e9e47c488b1a5de4d4cbc9f10ef36187`: local gates and CI run `32693450411` passed; release/deployment/production remain separately unverified |

There is deliberately no implementation plan for ML personalization, monetization, live streaming, native mobile, or production deployment. Those remain unapproved or premature under the MVP contract. Creating detailed build instructions for them would give agents false authority and recreate the non-determinism this index prevents.

## Reconciled Rollout State

The PR #11 handbook audited `main` at `dcf8d5cd3d18bb29dccb70dbce44405043a8adcb`. This rollout branch contains substantial later implementation. Findings therefore reconcile as follows:

| Handbook item | Rollout-branch state | Current action |
|---|---|---|
| C-001 admin authorization | PARTIAL | API `AdminUserDep` enforcement and denial tests are green at `bac7a89`; Next proxy remains transport-only and relies on FastAPI |
| C-002 unlisted discovery | RESOLVED | Global listing filters to `public`; Plan 1 preserves regression tests |
| C-003 response internals | RESOLVED | Product/operator schemas and frontend types are split at `fd62a20`/`d79b42f`; normal responses redact storage/task internals |
| C-004 upload race/idempotency | RESOLVED | Atomic upload claim and one active processing generation at `392f7af`; concurrent losers are rejected before storage/queue side effects |
| C-005 processing attempt ownership | RESOLVED | Generation propagation/fencing through `0ca718e`; bounded, dry-run-by-default stale recovery at `6bb8064` |
| C-006 partial HLS cleanup | RESOLVED | Attempt-scoped upload and failure cleanup at `8cf082a`; atomic inventory publication at `a417095` |
| C-007 storage deletion | RESOLVED | Tombstone-first original/processed cleanup and reconciliation at `bb27f28` |
| C-008 active-worker deletion fence | RESOLVED | Publication and finalize tombstone fences at `a417095` and `bb27f28` |
| C-009 segment inventory binding | RESOLVED | Inventory-bound proxy and signed delivery at `88ae38a` |
| C-010 telemetry governance | RESOLVED | Identity/deduplication at `7e0142a`; admission at `ef8b711`; retention at `6ee3323`; aggregate health at `5494bc9`; Plan 4 exit gate verified at `3021889` |
| C-011 strict Clerk `azp` | RESOLVED | Configured allowlists reject missing/mismatched `azp`; tests green at `ced7472` |
| C-012 stale watch copy | RESOLVED | User-safe lifecycle copy and smoke assertions at `d33d456` |
| Current-head/release evidence | COMPLETE | Plan 5 candidate `8e9b3244e9e47c488b1a5de4d4cbc9f10ef36187`; local gates and CI run `32693450411` passed; historical failures remain in the release audit |

Post-MVP product slices present on this branch include public discovery, channels, likes, watch later, Studio, comments, deterministic feeds, recommendation logging, thumbnails, moderation, analytics, captions, subscriptions, history, playlists, rich playback events, expanded media output, chapters, signed redirect delivery, Meilisearch indexing/read fallback, accessibility verification, and caption transcript search.

## Owner decisions recorded 2026-08-05

- D-011: keep `ATLAS_ADMIN_CLERK_USER_IDS` as the operator identity source.
- D-012: use asynchronous deletion status with an immediate tombstone and retryable cleanup.
- D-013: retain telemetry 30 days, cap admission at 120 events/minute/client/video, and persist no IP.
- CI release evidence will use an explicit Clerk-free smoke mode in CI; production and normal local auth remain Clerk-backed.
- R-001 (maximum upload size) remains open; agents must not infer a new limit.

These slices do not bypass the remediation sequence. Hardening Plans 1-5 are complete for the documented candidate. Recommendation V2 and ML remain deferred until the owner explicitly promotes that scope; merge, deployment, and production qualification remain separate approvals.

Plan 1 exit evidence is attributable to implementation commits `bac7a89`, `fd62a20`, `d79b42f`, `ced7472`, and `d33d456`, plus the contract documentation and memory handoff commit recorded below. C-001 remains partial by design: FastAPI is authoritative and the proxy does not independently authorize roles.

Plan 2 exit evidence is attributable to `6bb8064`, atop the generation-fencing commits through `0ca718e`. At that SHA, `make test` passed 115 API, 14 worker, and 5 web tests; `make lint` passed Compose validation, API/worker `compileall`, and web build/lint. `WEB_PORT=3002 WEB_SMOKE_URL=http://127.0.0.1:3002 make smoke` passed API/web/worker health, Alembic upgrade, privacy and API-mediated/API-proxied contract checks, upload through ready/HLS playback including master/rendition/segment/thumbnail, cross-user denial, and corrupt-media failure. The initial default-port smoke was blocked because unrelated `sandlabx-backend` owned `127.0.0.1:3001`; that attempt is not a pass, and no process was stopped. This is repository/local evidence only and does not claim merge, deployment, production, or Plan 3 completion.

Plan 3 implementation evidence is attributable to `5fb8d86` (publication/deletion schema), `8cf082a` (attempt-scoped staging and typed upload inventory), `a417095` (atomic publication), `88ae38a` (inventory-bound playback), `bb27f28` (tombstone-first deletion and reconciliation), and `83229d4` (cursor-batch remediation). The parent-verified exit gate at `83229d4` passed `make lint`, `make test` (130 API, 25 worker, 5 web), `WEB_PORT=3002 WEB_SMOKE_URL=http://127.0.0.1:3002 make smoke`, and `git diff --check`. Plan 3 is COMPLETE. This is repository/local evidence only and does not claim merge, deployment, authenticated browser qualification, or production readiness.

Plan 4 is COMPLETE at `3021889`. Implementation evidence is attributable to `7e0142a` (session/event identity), `47e54ff` (client identity remediation), `ef8b711` (Redis admission), `6ee3323` (raw-event retention), and `5494bc9` (aggregate operator health). The parent-verified exit gate passed `make lint`, `make test` (145 API, 25 worker, 9 web), `WEB_PORT=3003 WEB_SMOKE_URL=http://127.0.0.1:3003 make smoke`, and `git diff --check`. The same local verification included public-route Playwright checks, mobile overflow and keyboard focus checks, and Lighthouse accessibility 100 with zero failing audits on the rebuilt web artifact. These are local/browser artifacts only: merge, deployment, authenticated admin-role qualification, and production readiness remain unverified.

Plan 5 is COMPLETE at candidate `8e9b3244e9e47c488b1a5de4d4cbc9f10ef36187`. `make lint`, `make test` (149 API, 25 worker, 11 web), and exact-SHA `WEB_PORT=3009` smoke passed with fixed build time `2026-08-24T05:24:56Z`; CI run `32693450411` completed successfully with the same `head_sha`. Task 5.6 documentation changes are uncommitted in the shared worktree and require parent verification at the final documentation commit. Production remains `UNVERIFIED`.

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
