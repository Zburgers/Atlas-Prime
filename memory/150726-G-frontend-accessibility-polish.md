# 150726-G-frontend-accessibility-polish

Sector: G - Web Client and Playback
Agent: Codex
Date: 15-07-2026
Branch/Commit: docs/fullplatform-rollout

## What changed
- Consolidated shared frontend colours into named CSS tokens and retained the existing dark product visual system.
- Removed mobile primary-navigation horizontal scrolling, made compact history rows wrap safely, and added accessible loading/error announcements to home and watch flows.

## Decisions / ADR notes
- Decision: Apply focused shared-style and semantic fixes instead of a route-level redesign.
- Reason: The existing application already has a coherent operational video-platform layout; the audit found concrete responsiveness and live-region gaps rather than a need to replace information architecture.

## Validation
- `npm run lint`
- `npm test` (1 passed)
- `npm run build`
- Local Next server at `http://127.0.0.1:3010`; headless Chrome screenshots generated at 320, 375, 414, and 768px. Manually inspected 320px and 768px shells.

## Files touched
- apps/web/app/globals.css
- apps/web/app/components/video-list.tsx
- apps/web/app/watch/[videoId]/watch-client.tsx

## Handoff / risks
- Signed playback needs a configured CORS-enabled public MinIO endpoint before it can be browser-tested against real media objects.
- The current live server is intentionally left running on port 3010 for follow-up browser verification.
