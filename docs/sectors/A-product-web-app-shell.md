# Sector A — Product and Web App Shell

Owner: frontend/product agent  
Primary mission: make the streaming platform usable and visible in the browser.

## Scope

Build the MVP user-facing web experience:

- Next.js TypeScript app shell and App Router routes.
- Clerk auth integration points.
- Video library page.
- Upload/create video flow.
- Processing status UI.
- Watch page shell.
- Error/failed states.
- Minimal creator dashboard.

The frontend must make backend/media state understandable. It should not hide processing failures.

## Out of scope

- Complex social feed.
- Recommendations.
- Comments/likes.
- Creator monetization.
- Mobile-native apps.
- Heavy design system work before MVP functionality.

## Interfaces consumed

From Sector B:

- Video CRUD endpoints.
- Video status names.
- Processing status response.
- Playback metadata response shape.

From Sector F:

- Auth/session behavior.
- Ownership/permission failure semantics.

From Sector E:

- Playback metadata endpoint and API-owned HLS route.
- Player event endpoint if implemented.

From Sector G:

- Admin/debug status endpoint if shown in dashboard.

## Deliverables

- App shell/navigation.
- Clerk-wired sign-in/sign-up entry points or guarded routes as appropriate.
- Video list page.
- Create/upload video page.
- API-mediated upload UI that posts through FastAPI rather than directly to MinIO.
- Processing status component showing at least: queued, probing, processing, ready, failed.
- Watch page with hls.js player container.
- Failed-state display with user-safe message.
- Empty/loading/error states.
- Minimal responsive layout.

## Acceptance criteria

- [ ] User can navigate from video list to upload/create page.
- [ ] User can upload/select a local video through the UI when API is ready.
- [ ] UI shows backend video status without inventing incompatible states.
- [ ] New videos are treated as private by default in create/edit UI.
- [ ] Failed processing is visible and not treated as infinite loading.
- [ ] Watch page can play API-owned HLS URLs once Sector E is ready.
- [ ] Unauthorized/forbidden API responses show clear UI feedback.
- [ ] UI does not hardcode local filesystem paths.
- [ ] UI does not hardcode MinIO bucket/object paths.
- [ ] At least one UI smoke path is documented.

## Suggested implementation order

1. Build layout, routes, and empty states.
2. Add typed API client or equivalent request layer.
3. Implement video list and detail views.
4. Implement upload flow.
5. Implement status polling or refresh.
6. Integrate HLS player from Sector E.
7. Add minimal dashboard/debug view if G exposes data.

## Latest docs to check

- Next.js docs.
- Clerk frontend/Next.js docs if auth UI or route protection is touched.
- hls.js docs if player logic is touched: https://github.com/video-dev/hls.js/
- Browser Media Source Extensions docs if debugging playback behavior: https://developer.mozilla.org/en-US/docs/Web/API/Media_Source_Extensions_API


## Required memory entry

Before handoff, write:

```txt
memory/DDMMYY-A-short-topic.md
```

Use `memory/_TEMPLATE.md`. Include changed interfaces, validation, and handoff risks.

## Required grounding

Before implementation, read:

- `docs/00-ground-truth-mvp-spec.md`
- `docs/01-agent-operating-contract.md`
- This sector manifest
- Recent `memory/` entries for this sector and direct dependencies
- Latest official docs for any framework/tool/API touched
