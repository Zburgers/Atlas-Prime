# 280626-F-clerk-auth-wiring

Sector: F authentication and access control
Agent: Codex
Date: 28-06-2026
Branch/Commit: main / uncommitted

## What changed
- Added Clerk Next.js provider, middleware proxy, sign-in/sign-up routes, and a signed-in API identity check on the MVP page.
- Replaced default API dev-header identity with Clerk session JWT verification via bearer token or `__session` cookie.
- Added optional-user read/playback authorization so anonymous access is limited to ready `public`/`unlisted` videos; owner-only states remain protected.
- Kept dev identity headers behind `ATLAS_ALLOW_DEV_AUTH_HEADERS=true` for local tests/smoke only.

## Decisions / ADR notes
- Decision: Verify Clerk session tokens in FastAPI with JWKS-backed RS256 validation and `azp` origin checks.
- Reason: Matches the MVP Clerk JWT contract without adding custom passwords or server-side sessions.
- Alternatives considered: Continuing dev headers by default, rejected because Sector F requires real Clerk identity before non-local use.

## Validation
- `clerk init --app app_3Fldg6OPLlGBAMmcAv2bDYuT0PD -y` from `apps/web`
- `clerk doctor --json` from `apps/web` (passes; warns only that production instance and shell completion are not configured)
- `pytest` from `apps/api` (13 passed)
- `npm --workspace apps/web test`
- `npm --workspace apps/web run lint`
- `npm --workspace apps/web run build`
- `make test`
- `make lint`
- `make smoke`

## Files touched
- apps/api/app/api/deps.py
- apps/api/app/services/auth.py
- apps/api/app/services/videos.py
- apps/api/tests/test_clerk_auth.py
- apps/api/tests/test_video_api.py
- apps/web/app/layout.tsx
- apps/web/app/components/api-status.tsx
- apps/web/app/sign-in/[[...sign-in]]/page.tsx
- apps/web/app/sign-up/[[...sign-up]]/page.tsx
- apps/web/proxy.ts
- compose.yaml
- docs/api-database.md
- docs/local-dev.md

## Handoff / risks
- Root `.env` and `apps/web/.env.local` were populated locally through Clerk CLI and are intentionally ignored.
- Sector C upload routes should use `CurrentUserDep` and owner helpers for mutations; Sector E HLS proxy should reuse `video_with_renditions_for_playback` for access checks.
- Production Clerk instance is not configured yet; local/dev is linked to `app_3Fldg6OPLlGBAMmcAv2bDYuT0PD`.
