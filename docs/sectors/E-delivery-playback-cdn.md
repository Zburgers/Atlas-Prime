# Sector E — Delivery, Playback, and CDN Pathing

Owner: playback/delivery agent  
Primary mission: serve generated HLS outputs safely and play them in the browser.

## Scope

Build the delivery/playback path:

- Static serving of processed HLS assets.
- Playback metadata endpoint integration.
- Browser HLS player.
- Basic quality/error/loading events.
- Cache-header pathing that can later be moved behind CDN.
- Optional signed playback URL support if Sector F is ready.

## Out of scope

- Full CDN vendor integration as a hard MVP requirement.
- DRM.
- Low-latency streaming.
- Live playback.
- Advanced QoE analytics platform.

## Interfaces consumed

From Sector B:

- Playback metadata endpoint.
- Video ready status.
- HLS master storage key.

From Sector D:

- HLS output layout and manifest location.

From Sector F:

- Access checks and signed URL/token rules if implemented.

From Sector A:

- Watch page/player container.

## Interfaces provided

To Sector A:

- Player component or playback integration pattern.
- Error/loading/ready states.

To Sector G:

- Playback events if implemented.
- Player error payloads.

## Delivery contract

The frontend should receive playback information from the API, not by guessing paths.

Example shape:

```json
{
  "video_id": "...",
  "status": "ready",
  "hls_master_url": "https://.../processed/{video_id}/hls/master.m3u8",
  "thumbnail_url": "https://.../processed/{video_id}/hls/thumbnail.jpg"
}
```

For local MVP, the URL may be served by the API, Next.js static route, or Nginx, but the abstraction should allow CDN later.

## Deliverables

- Static serving configuration or route.
- HLS playback integration.
- Watch-page integration with Sector A.
- User-visible playback error handling.
- Optional player event reporting endpoint usage.
- Basic cache-header documentation.
- CDN migration notes.

## Acceptance criteria

- [ ] A ready video's `master.m3u8` can be fetched through an HTTP URL.
- [ ] Browser watch page plays generated HLS output.
- [ ] Player handles loading, error, and unsupported-browser cases.
- [ ] Playback URL is obtained from API.
- [ ] Private/non-owned video playback is denied if privacy/auth is enabled.
- [ ] Static delivery does not expose arbitrary filesystem browsing.
- [ ] Cache headers are reasonable for immutable segment files.
- [ ] Local delivery path can later be fronted by CDN without changing D's output format.

## Suggested implementation order

1. Serve processed HLS directory safely.
2. Add playback metadata endpoint integration.
3. Add player library/component.
4. Wire watch page.
5. Add player error handling.
6. Add basic event reporting if planned.
7. Document CDN migration path.

## Latest docs to check

- hls.js docs: https://github.com/video-dev/hls.js/
- Browser Media Source Extensions overview: https://developer.mozilla.org/en-US/docs/Web/API/Media_Source_Extensions_API
- Static file serving docs for chosen backend/reverse proxy.
- CDN/cache docs if vendor-specific config is added.

## Required memory entry

Before handoff, write:

```txt
memory/DDMMYY-E-short-topic.md
```

Use `memory/_TEMPLATE.md`. Include changed interfaces, validation, and handoff risks.

## Required grounding

Before implementation, read:

- `docs/00-ground-truth-mvp-spec.md`
- `docs/01-agent-operating-contract.md`
- This sector manifest
- Recent `memory/` entries for this sector and direct dependencies
- Latest official docs for any framework/tool/API touched
