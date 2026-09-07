# Release Evidence: PR #12 Merge-Readiness Candidate

Status: the implementation candidate is locally qualified and has passed the exact-source end-to-end smoke. Merge, deployment, authenticated browser qualification, and production remain unverified.

## Candidate

- Branch: `docs/fullplatform-rollout`
- Implementation candidate SHA: `aee06a58888db8cc4f5536381dfbf4712655ebb0`
- Pull request: [#12](https://github.com/Zburgers/Atlas-Prime/pull/12)
- Main base: `8d0ebc5f7c08d66c2d5edbe910c1aee740bed9b3`
- Fixed build metadata used by the final smoke:
  - `ATLAS_BUILD_SHA=aee06a58888db8cc4f5536381dfbf4712655ebb0`
  - `ATLAS_BUILD_TIME=2026-09-08T08:00:00Z`

## Local Gates

- API: `PYTHONPATH=. pytest -q tests` — PASS, `152 passed`.
- Worker: `docker run --rm atlas-prime-worker:latest pytest -q tests` — PASS, `25 passed`.
- Web: `npm --workspace apps/web test` — PASS, `11 passed`.
- Web lint/build, API/worker `compileall`, and `docker compose config -q` — PASS.
- Migration: `apps/api/alembic upgrade head` — PASS at `20260908_0020`.
- Exact-SHA stack smoke — PASS on alternate ports (`API_PORT=18000`, `WEB_PORT=3011`): readiness, dependency health, Alembic, `/version` SHA assertion, API-mediated upload, worker processing, ready HLS playback, private playback denial, and corrupt-media failure.
  - Ready video: `aeb4e911-3091-42cf-b9f1-2ad2af0b9580`.
  - Bad video: `d88c5b95-4bed-4016-87cb-ce961cbf8950`; failure code `MEDIA_COMMAND_FAILED`.
- `git diff --check` — PASS after the implementation commits.

## Blocker Reconciliation

The eight merge-blocking review findings are addressed in the candidate:

| Finding | Resolution |
|---|---|
| B1 public comment identity | Public comment responses use a generic viewer label. |
| B2 visibility drift | Shared discoverable/direct-link predicates cover moderation and tombstones across feeds, search, channels, subscriptions, history, and playlists. |
| B3 publish-before-commit | Upload and Studio queueing commit a durable dispatch intent before broker publication; reconciliation is available through `make processing-reconcile`. |
| B4 manual process publication | The manual process route uses the same canonical durable publisher. |
| B5 anonymous telemetry trust | Anonymous admission uses a signed server-issued HttpOnly session cookie; impressions/views use the same admission and bounded deduplication. |
| B6 counter races | Reaction and telemetry writes use conflict-safe inserts and atomic counter updates. |
| B7 playlist positions | Playlist rows are locked and the next position is derived from `MAX(position)`, with a middle-delete regression test. |
| B8 stale evidence | This record and the PR now identify the exact candidate SHA and CI run. |

## GitHub Actions Evidence

- Run: [CI run 34169243078](https://github.com/Zburgers/Atlas-Prime/actions/runs/34169243078)
- Event: `pull_request`
- `head_sha`: `aee06a58888db8cc4f5536381dfbf4712655ebb0`
- Required check: `devex` passed (job [101886243809](https://github.com/Zburgers/Atlas-Prime/actions/runs/34169243078/job/101886243809)).
- Status/conclusion: `completed` / `success`.

## Evidence Boundaries

This record proves local qualification and attributable CI qualification for the implementation candidate. It does not prove merge, deployment, authenticated admin-role qualification, or production behavior. Production: `UNVERIFIED`.
