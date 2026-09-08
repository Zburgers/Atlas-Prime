# Release Evidence: PR #12 Merge-Readiness Candidate

Status: the implementation candidate is locally qualified and has passed exact-head CI (including the devex stack smoke). Merge, deployment, authenticated browser qualification, and production remain unverified.

## Candidate

- Branch: `docs/fullplatform-rollout`
- Implementation candidate SHA: `266b4600a3973753357a46800c96460aae2cbcfc`
- Pull request: [#12](https://github.com/Zburgers/Atlas-Prime/pull/12)
- Main base: `8d0ebc5f7c08d66c2d5edbe910c1aee740bed9b3`
- Prior candidate superseded by this one: `aee06a58888db8cc4f5536381dfbf4712655ebb0` (CI run `34169243078`).

## Implementation Candidate vs Docs-Inclusive Head

- The implementation candidate (`266b460`) is the last commit that changes runtime behavior. It closes the reopened telemetry abuse finding (rotation-proof anonymous admission, stable secret contract, adversarial tests).
- Any later docs-inclusive head on this branch contains only this evidence file, the PR body, and review-thread replies on top of the candidate. The code delta from candidate to docs head is documentation-only.
- The exact final docs-inclusive head SHA and its exact green CI run are recorded in the PR body (they cannot be embedded in this file without invalidating the SHA they describe; the body is mutable without a new commit).

## Local Gates (at the candidate SHA)

- API: `PYTHONPATH=. pytest -q tests` — PASS, `156 passed` (152 carried + 4 new telemetry tests).
- API/worker `compileall` and `git diff --check` — PASS.
- Web: unchanged by this candidate; exact-head CI re-ran `npm --workspace apps/web test` — PASS (prior local: `11 passed`).
- Worker: unchanged by this candidate (no shared code; `workers/` imports nothing from `apps/api/app`); prior local worker result carried: `25 passed`.
- Migration: no schema change in this candidate (telemetry-only service/route change).
- Exact-head stack smoke (`./scripts/smoke-devex.sh`) — PASS inside the CI run below (readiness, dependency health, upload, processing, HLS playback).

## Blocker Reconciliation

The eight merge-blocking review findings, plus the two reopened final-head findings, are addressed in the candidate:

| Finding | Resolution |
|---|---|
| B1 public comment identity | Public comment responses use a generic viewer label. |
| B2 visibility drift | Shared discoverable/direct-link predicates cover moderation and tombstones across feeds, search, channels, subscriptions, history, and playlists. |
| B3 publish-before-commit | Upload and Studio queueing commit a durable dispatch intent before broker publication; reconciliation is available through `make processing-reconcile`. |
| B4 manual process publication | The manual process route uses the same canonical durable publisher. |
| B5 anonymous telemetry trust (reopened: cookie rotation) | Anonymous admission uses a server-derived per-video bucket (`anon` scope bound to server-known video id + server-time window). No client-controlled value (cookie, session UUID, request id) can mint a fresh bucket; adversarial cookie-rotation tests prove 150 rotated writes yield exactly 120 accepted / 30 rate-limited with bounded rows and counters. |
| B5b telemetry secret contract (reopened) | `ATLAS_TELEMETRY_SECRET` is documented in `.env.example`. A configured secret is always preferred; development falls back to an ephemeral per-process secret with a one-time warning; other environments fail anonymous telemetry closed (503) while authenticated telemetry keeps working. Covered by fail-closed and dev-fallback tests. |
| B6 counter races | Reaction and telemetry writes use conflict-safe inserts and atomic counter updates. |
| B7 playlist positions | Playlist rows are locked and the next position is derived from `MAX(position)`, with a middle-delete regression test. |
| B8 stale evidence | This record distinguishes the implementation candidate from the docs-inclusive head and names the exact CI run below; the final head/run mapping is tracked in the PR body. |

## GitHub Actions Evidence

- Run: [CI run 34201068181](https://github.com/Zburgers/Atlas-Prime/actions/runs/34201068181)
- Event: `pull_request`
- `head_sha`: `266b4600a3973753357a46800c96460aae2cbcfc`
- Required check: `devex` passed (job [101979716714](https://github.com/Zburgers/Atlas-Prime/actions/runs/34201068181/job/101979716714)).
- Status/conclusion: `completed` / `success`.
- Final docs-head run: [CI run 34201318859](https://github.com/Zburgers/Atlas-Prime/actions/runs/34201318859) on `9c14a329ecfb2fc0491a6c0dc4074c5f7b0db533` — `completed` / `success`. The current HEAD adds only this run-id line on top of `9c14a32`; its own exact-head run is recorded in the PR body (embedding that future run id in-tree would itself invalidate the HEAD it describes).

## Evidence Boundaries

This record proves local qualification and attributable CI qualification for the implementation candidate. It does not prove merge, deployment, authenticated admin-role qualification, or production behavior. Production: `UNVERIFIED`.
