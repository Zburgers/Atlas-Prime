# 240826-H-ci-smoke-clerk-remediation

Sector: H — testing, DevEx, and CI
Agent: Luna
Date: 24-08-2026
Branch/Commit: `docs/fullplatform-rollout` / `129b3dacb85661bdd7b0bc067b0195feb66933b3`, uncommitted changes

## What changed
- Root cause: the unchanged `apps/web/proxy.ts` unconditionally evaluated `clerkMiddleware()`, so blank CI publishable values reached Clerk before the smoke-only layout.
- The previous fake `pk_test_` workaround was rejected by Clerk runtime as `Publishable key not valid.` and has been removed from `scripts/smoke-devex.sh`.
- `apps/web/proxy.ts` now uses the exact server-side condition `ATLAS_CI_SMOKE_MODE === "true"` to return `NextResponse.next()` without initializing Clerk; normal startup still uses `clerkMiddleware()`.
- Added a web-local source regression for the explicit bypass and normal Clerk middleware. The existing fake `sk_test_` smoke secret and exact assertion remain.

## Decisions / ADR notes
- Decision: bypass the Next middleware only for the disposable exact-true smoke process; preserve normal Clerk initialization, matcher configuration, API auth, and production behavior.
- Reason: fake publishable keys are syntactically prefixed but invalid at Clerk runtime, while CI smoke intentionally has no real Clerk frontend credentials.
- Alternatives considered: retaining fake publishable keys was rejected after live runtime failure; weakening the layout or changing Docker context was not needed.

## Validation
- Pre-fix red phase: the new web-local middleware assertion failed against the unconditional `export default clerkMiddleware()` source.
- `docker compose run --rm --build web-test npm --workspace apps/web test`: PASS, 11 tests.
- `docker compose run --rm --build web-test npm --workspace apps/web run lint`: PASS.
- `sh -n scripts/smoke-devex.sh`: PASS.
- `docker compose config -q`: PASS.
- `git diff --check`: PASS.
- Disposable smoke command with blank publishable values, `WEB_PORT=3008`, `ATLAS_BUILD_SHA=129b3dacb85661bdd7b0bc067b0195feb66933b3`, and `ATLAS_BUILD_TIME=2026-08-24T05:12:00Z`: PASS. API and web readiness passed at `http://127.0.0.1:3008`; full integration smoke passed with ready video `a4d1c727-c161-4357-b36c-e2f4365e0830` and failed video `9f820749-507c-47cf-9bf2-51c1dbfe6098`, failure code `MEDIA_COMMAND_FAILED`.
- No GitHub Actions rerun, authenticated browser QA, production deployment, commit, or push was performed.

## Files touched
- `apps/web/proxy.ts`
- `apps/web/tests/smoke.test.js`
- `scripts/smoke-devex.sh`
- `memory/240826-H-ci-smoke-clerk-remediation.md`

## Handoff / risks
- The local smoke proves blank publishable-key startup and full smoke behavior at the candidate SHA/time, but does not establish a green remote run. Parent should run a new GitHub Actions check before closing the gate.
- Changes remain uncommitted and unpushed for parent review. No real credentials were added to files or output.
