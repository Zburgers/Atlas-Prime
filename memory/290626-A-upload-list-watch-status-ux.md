# 290626-A-upload-list-watch-status-ux

Sector: A product and web app shell
Agent: Codex
Date: 29-06-2026
Branch/Commit: main / committed

## What changed
- Added the MVP library, upload, and watch/status routes in the Next.js app.
- Added typed frontend API helpers and a same-origin `/api/backend/*` proxy to FastAPI.
- Added hls.js watch-page wiring for API-owned playback URLs once Sector E serves HLS.
- Added Docker web runtime `ATLAS_API_BASE_URL` so server-side proxy calls use the Compose API hostname.

## Decisions / ADR notes
- Decision: Keep browser API calls same-origin through the Next.js proxy while still sending Clerk bearer tokens from client components.
- Reason: Avoids frontend CORS coupling and keeps the browser from learning MinIO or filesystem paths.
- Alternatives considered: Direct browser calls to FastAPI, which worked for health checks but is more brittle for authenticated multipart upload.

## Validation
- `npm --workspace apps/web run lint`
- `npm --workspace apps/web run build`
- `npm --workspace apps/web test`
- `docker compose config -q`
- `docker compose up -d --build web`
- `curl -fsS http://localhost:3001/`
- `curl -fsS http://localhost:3001/upload`
- `curl -fsS http://localhost:3001/watch/00000000-0000-0000-0000-000000000000`
- `curl -fsS http://localhost:3001/api/backend/healthz/live`
- `make smoke`
- `make test`

## Files touched
- apps/web/app/page.tsx
- apps/web/app/layout.tsx
- apps/web/app/api/backend/[...path]/route.ts
- apps/web/app/components/
- apps/web/app/upload/
- apps/web/app/watch/[videoId]/
- apps/web/app/globals.css
- apps/web/package.json
- package-lock.json
- compose.yaml
- .env.example

## Handoff / risks
- Signed browser upload still requires an active Clerk session; dev auth headers are disabled in the running API.
- Sector D is still required for queued videos to become ready.
- Sector E is still required for `/videos/{video_id}/hls/{path}` to serve real HLS assets.
- Chrome DevTools browser smoke could not run in this environment because its connector tried to start a headful browser without an X server.
