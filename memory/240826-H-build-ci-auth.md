# 240826-H-build-ci-auth

Sector: H — testing, DevEx, and CI
Agent: Luna
Date: 24-08-2026
Branch/Commit: `docs/fullplatform-rollout` / `a8350b2` base, uncommitted changes

## What changed
- Added exact-`true` `ATLAS_CI_SMOKE_MODE` runtime handling in the Next root layout: smoke renders a minimal semantic shell without ClerkProvider; normal mode remains Clerk-backed and throws when the publishable key is absent.
- Scoped `ATLAS_CI_SMOKE_MODE=true`, `ATLAS_ALLOW_DEV_AUTH_HEADERS=true`, and a disposable non-secret Clerk middleware placeholder to the smoke script/CI smoke step; normal `.env.example` defaults remain unchanged.
- Passed the smoke flag and existing `CLERK_SECRET_KEY` through the web Compose runtime. The secret mapping is required because the unchanged Clerk middleware executes before the layout; smoke supplies only the placeholder.

## Decisions / ADR notes
- Decision: keep `apps/web/proxy.ts` and normal Clerk auth unchanged; use a smoke-only shell and process-scoped middleware bootstrap instead of weakening proxy authorization.
- Reason: Clerk middleware requires initialization even when the smoke layout omits all Clerk components, while CI has no real Clerk credentials.
- Path drift: the requested `docs/sectors/sector-g.md` and `sector-h.md` names are not present; the repository manifests are `G-observability-admin-ops.md` and `H-testing-devex-ci.md`.

## Validation
- `docker compose run --rm --build web-test npm --workspace apps/web test`: PASS, 10 tests.
- `docker compose run --rm --build web-test npm --workspace apps/web run lint`: PASS.
- `docker compose run --rm --build web-test npm --workspace apps/web run build`: PASS; Next.js 16.2.9 build and TypeScript completed.
- `docker compose config -q`, `sh -n scripts/smoke-devex.sh`, source `rg` checks, and `git diff --check`: PASS.
- Disposable web runtime with blank Clerk publishable keys and smoke mode true returned HTTP 200 for `/`; normal mode with blank Clerk configuration returned HTTP 500 fail-closed. No authenticated browser or production evidence was claimed.

## Files touched
- `.github/workflows/ci.yml`
- `compose.yaml`
- `scripts/smoke-devex.sh`
- `apps/web/app/layout.tsx`
- `apps/web/tests/smoke.test.js`
- `memory/240826-H-build-ci-auth.md`

## Handoff / risks
- The committed smoke placeholder is not a real credential and is exported only by `smoke-devex.sh`; it must never be copied into `.env` or production configuration.
- The smoke shell intentionally does not render authenticated page components; normal Clerk-backed page rendering is preserved outside exact smoke mode.
- Changes are uncommitted and unpushed for parent review. Plan 5.2+ work remains untouched.
