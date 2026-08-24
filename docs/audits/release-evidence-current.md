# Release Evidence: Current Local Candidate

Status: local deterministic candidate qualification recorded; CI, deployment, and production remain unverified.

## Candidate

- Branch: `docs/fullplatform-rollout`
- Candidate SHA: `a34e20ecd372e1aea429b461f55a34413120ac56`
- Source-control state: `origin/docs/fullplatform-rollout` matched the candidate before the gate. The working tree was clean before and after the gate.
- Fixed build metadata for all three gates:
  - `ATLAS_BUILD_SHA=a34e20ecd372e1aea429b461f55a34413120ac56`
  - `ATLAS_BUILD_TIME=2026-08-24T04:57:32Z`

## Validation Window

The parent-verified gate ran on 2026-08-24. Candidate setup timestamp was `2026-08-24T04:57:32Z`; completion was observed at `2026-08-24T05:00:38Z`. These are window boundaries, not per-command timestamps.

## Gates

Each command used the fixed build metadata above.

1. `ATLAS_BUILD_SHA=a34e20ecd372e1aea429b461f55a34413120ac56 ATLAS_BUILD_TIME=2026-08-24T04:57:32Z make lint`
   - PASS: Compose configuration, API/worker `compileall`, and web build/lint.
2. `ATLAS_BUILD_SHA=a34e20ecd372e1aea429b461f55a34413120ac56 ATLAS_BUILD_TIME=2026-08-24T04:57:32Z make test`
   - PASS: 149 API tests, 25 worker tests, and 10 web tests.
3. `ATLAS_BUILD_SHA=a34e20ecd372e1aea429b461f55a34413120ac56 ATLAS_BUILD_TIME=2026-08-24T04:57:32Z WEB_PORT=3005 API_SMOKE_URL=http://127.0.0.1:8000 WEB_SMOKE_URL=http://127.0.0.1:3005 make smoke`
   - PASS: API, web, and dependency health; Alembic upgrade; `/version` SHA assertion; upload through processing to ready HLS playback; private playback denial; and corrupt-media failure. Web HTTP was 200.

Additional post-gate checks:

- `git diff --check`: PASS.
- `git status --porcelain=v1`: empty after the gate.

Observed `/version` response after smoke:

```json
{"build_sha":"a34e20ecd372e1aea429b461f55a34413120ac56","build_time":"2026-08-24T04:57:32Z","app_environment":"development","alembic_head":"20260824_0019"}
```

## Evidence Boundaries

This record proves local deterministic candidate qualification only. The pushed remote ref is source-control state, not CI proof. The GitHub Actions check head SHA is not yet verified; Plan 5.5 remains open. Merge, deployment, authenticated browser qualification for this candidate, and production status are not claimed. Production: `UNVERIFIED`.
