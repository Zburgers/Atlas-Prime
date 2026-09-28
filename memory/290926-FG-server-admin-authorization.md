# 290926-FG-server-admin-authorization

Sector: F — Auth & Access Control; G — Observability/Admin Ops
Agent: Codex + GPT-6-Luna builder
Date: 29-09-2026
Branch/Commit: `codex/plan6-1-admin-auth` / `0e09e32`

## What changed
- Added a server-side Clerk allowlist guard for all `/admin/*` pages and the `/api/backend/admin/*` proxy.
- Reused `ATLAS_ADMIN_CLERK_USER_IDS`; empty configuration denies admin access. FastAPI remains authoritative.

## Decisions / ADR notes
- Decision: No ADR-level decision; implements existing D-011 as web defense in depth.
- Reason: Admin pages and proxy must deny signed-out/non-admin sessions before rendering or forwarding.

## Validation
- `make lint` passed, including Next.js lint/build and TypeScript checks.
- `make test`: API 158 passed, worker 25 passed, web 13 passed.
- Focused API tests: 43 passed; `docker compose config -q` and `git diff --check` passed.
- `WEB_PORT=3001 WEB_SMOKE_URL=http://127.0.0.1:3001 make smoke` passed; full-stack containers left running for local testing.
- Exact-head GitHub CI pending PR creation.

## Files touched
- `apps/web/app/admin/`
- `apps/web/app/api/backend/[...path]/route.ts`
- `apps/web/tests/smoke.test.js`
- `compose.yaml`, `.env.example`, `docs/observability-admin-ops.md`

## Handoff / risks
- Set the same allowlist for API and web using `ATLAS_ADMIN_CLERK_USER_IDS`; never expose it as `NEXT_PUBLIC_*`.
- Clerk-authenticated browser paths still require the user's own configured Clerk account; the smoke run used its disposable test mode.
- Keep the change on its own PR; do not merge without the owner’s merge authorization.
