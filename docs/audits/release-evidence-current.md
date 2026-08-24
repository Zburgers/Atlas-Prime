# Release Evidence: Qualified Implementation Candidate

Status: local deterministic and attributable CI candidate qualification recorded; merge, deployment, authenticated browser qualification, and production remain unverified.

## Candidate

- Branch: `docs/fullplatform-rollout`
- Candidate SHA: `8e9b3244e9e47c488b1a5de4d4cbc9f10ef36187`
- Source-control state: local `HEAD` and `origin/docs/fullplatform-rollout` matched this SHA before documentation closeout. The working tree was clean before these documentation changes.
- Pull request: [#12](https://github.com/Zburgers/Atlas-Prime/pull/12), open, `headRefOid` matches the candidate.
- Fixed build metadata:
  - `ATLAS_BUILD_SHA=8e9b3244e9e47c488b1a5de4d4cbc9f10ef36187`
  - `ATLAS_BUILD_TIME=2026-08-24T05:24:56Z`

## Local Gates

Each gate used the fixed build metadata above.

1. `ATLAS_BUILD_SHA=8e9b3244e9e47c488b1a5de4d4cbc9f10ef36187 ATLAS_BUILD_TIME=2026-08-24T05:24:56Z make lint`
   - PASS: Compose configuration, API/worker `compileall`, and web build/lint.
2. `ATLAS_BUILD_SHA=8e9b3244e9e47c488b1a5de4d4cbc9f10ef36187 ATLAS_BUILD_TIME=2026-08-24T05:24:56Z make test`
   - PASS: 149 API tests, 25 worker tests, and 11 web tests.
3. `ATLAS_BUILD_SHA=8e9b3244e9e47c488b1a5de4d4cbc9f10ef36187 ATLAS_BUILD_TIME=2026-08-24T05:24:56Z WEB_PORT=3009 API_SMOKE_URL=http://127.0.0.1:8000 WEB_SMOKE_URL=http://127.0.0.1:3009 make smoke`
   - PASS: API/web/dependency readiness, Alembic upgrade, `/version` SHA assertion, ready HLS upload/process/playback, private playback denial, and corrupt-media failure.
   - Ready video: `aad0f4b9-9e9c-409e-81df-57e7bcb5a38e`.
   - Bad video: `c718d081-9fca-4a1b-933f-faa684638d9a`; failure code `MEDIA_COMMAND_FAILED`.

Additional post-gate check: `git diff --check` PASS before documentation closeout.

## Final Documentation-Inclusive Verification

The documentation-only follow-up head `d5c5ba07d9bedb58d69eca6308ee69d0a991e72f` was independently requalified after the closeout commit. The implementation candidate above remained unchanged.

- Fixed build metadata: `ATLAS_BUILD_SHA=d5c5ba07d9bedb58d69eca6308ee69d0a991e72f`, `ATLAS_BUILD_TIME=2026-08-24T05:38:04Z`.
- Parent rerun: `make lint` PASS; `make test` PASS with 149 API, 25 worker, and 11 web tests.
- Parent rerun: `WEB_PORT=3010` smoke PASS with readiness, dependency health, Alembic, `/version` SHA assertion, ready HLS playback, private denial, and corrupt-media failure.
- CI run [32694224817](https://github.com/Zburgers/Atlas-Prime/actions/runs/32694224817) completed successfully with `head_sha` `d5c5ba07d9bedb58d69eca6308ee69d0a991e72f`; `devex` passed at [job 97333246149](https://github.com/Zburgers/Atlas-Prime/actions/runs/32694224817/job/97333246149).

## `/version` Contract

The smoke assertion passed for the exact candidate SHA and fixed build time. The response contract is the exact field set:

```json
{"build_sha":"<candidate SHA>","build_time":"<fixed build time>","app_environment":"<environment>","alembic_head":"<migration head>"}
```

No host path, token, storage credential, or other secret is part of this contract.

## GitHub Actions Evidence

- Run: [CI run 32693450411](https://github.com/Zburgers/Atlas-Prime/actions/runs/32693450411)
- Event: `pull_request`
- Status/conclusion: `completed` / `success`
- `head_sha`: `8e9b3244e9e47c488b1a5de4d4cbc9f10ef36187`
- Required check: `devex` passed at [job 97331148718](https://github.com/Zburgers/Atlas-Prime/actions/runs/32693450411/job/97331148718)

## Historical Failure Context

- Run [32692193463](https://github.com/Zburgers/Atlas-Prime/actions/runs/32692193463) on prior head `129b3dacb85661bdd7b0bc067b0195feb66933b3` failed only at Sector H web readiness because CI had no Clerk publishable key while `apps/web/proxy.ts` initialized Clerk before the smoke-only layout.
- The first fake `pk_test_` workaround also failed in a live local container with `Publishable key not valid.` The committed remediation is the exact smoke-mode proxy bypass, which is covered by the current local and CI evidence.

## Evidence Boundaries

This record proves deterministic local qualification and attributable GitHub Actions qualification for the implementation candidate and its documentation-inclusive follow-up head. It does not prove branch merge, deployment, authenticated browser qualification, or production behavior. Production: `UNVERIFIED`.
