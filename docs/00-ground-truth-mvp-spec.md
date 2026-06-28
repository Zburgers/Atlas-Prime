# Ground Truth MVP Spec — Atlas Prime

Status: canonical planning document  
Audience: all sector agents and the human engineering owner  
Last updated: 28-06-2026

## 1. Mission

Build Atlas Prime: a from-scratch, self-hostable video-on-demand streaming platform for learning purposes.

The MVP must prove this complete loop:

```txt
user signs in
  -> uploads a video
  -> backend stores original media
  -> processing job inspects and transcodes the video
  -> HLS renditions and playlists are generated
  -> video status becomes ready
  -> user watches the video in a browser player
  -> system exposes enough logs/status to debug failures
```

The project should teach real streaming architecture while staying small enough for iterative engineering.

## 2. Product definition

The MVP is a small YouTube-like VOD system, not a full public platform.

### In scope

- User authentication.
- Video upload.
- Upload progress/status where feasible.
- Video metadata: title, description, owner, status, duration, dimensions, codec info.
- Background processing jobs.
- `ffprobe`-based media inspection.
- FFmpeg-based transcoding/packaging.
- HLS output using a master playlist plus at least two renditions.
- Browser playback using an HLS-capable player.
- Basic video library/list page.
- Basic watch page.
- Basic creator dashboard showing processing state and failure reasons.
- MinIO-backed object storage from day one.
- Minimal but reliable logs, error states, and handoff notes.
- Tests and smoke validation for the critical upload -> process -> playback path.

### Explicitly out of scope for MVP

- Live streaming.
- Real CDN integration as a hard requirement.
- Multi-region distribution.
- DRM/Widevine/FairPlay/PlayReady.
- Payments, subscriptions, ads, creator payouts.
- Recommendation algorithms.
- Comments, likes, social feed, notifications.
- Mobile apps.
- Advanced content moderation.
- Distributed transcoding autoscaling.
- GPU transcoding.
- Multi-audio-track UX.
- Full subtitle generation pipeline.
- Public search engine.

These may become future phases, but they must not block the first complete VOD loop.

## 3. Confirmed MVP architecture

The confirmed stack for Atlas Prime MVP is:

| Layer | Confirmed choice | Rationale |
|---|---|---|
| Frontend | Next.js with TypeScript/React | Fast product iteration, App Router-compatible routes, simple watch/upload pages |
| API | FastAPI | Clean HTTP contracts, Python media orchestration, straightforward dependency injection |
| ORM/migrations | SQLAlchemy ORM + Alembic | Durable schema management and explicit database evolution |
| Database | PostgreSQL | Durable relational state and predictable querying |
| Queue | Redis + Celery | Standard Python background processing stack for media jobs |
| Worker | FFmpeg + ffprobe | Direct exposure to media processing fundamentals |
| Auth | Clerk with JWT-backed API verification | Outsources auth while preserving ownership checks in the API |
| Storage | MinIO/S3-compatible object storage from day one | Same object-storage contract for API, worker, and future deployment |
| Upload transport | API-mediated upload through FastAPI into MinIO | Simplest MVP validation/auth path; presigned direct upload is deferred |
| Delivery | Authenticated FastAPI HLS proxy backed by MinIO | Preserves private-by-default playback without making MinIO objects public |
| Player | hls.js on an HTML video element | Browser HLS playback with MSE support |
| Local orchestration | Docker Compose | Repeatable dev environment for web, API, PostgreSQL, Redis, worker, and MinIO |

Agents must use these choices unless the human owner explicitly expands scope and the change is recorded as an ADR-level memory entry.

## 4. Canonical video lifecycle

Every video must move through a clear state machine.

```txt
draft
  -> uploading
  -> uploaded
  -> queued
  -> probing
  -> processing
  -> ready
  -> failed
```

Minimum required state behavior:

| State | Meaning |
|---|---|
| `draft` | DB row exists but upload has not completed. |
| `uploading` | Upload has started. |
| `uploaded` | Original file exists and is ready for validation/probing. |
| `queued` | Processing job has been created. |
| `probing` | Worker is inspecting media metadata. |
| `processing` | Worker is transcoding/packaging. |
| `ready` | HLS output exists and playback URL is available. |
| `failed` | Processing/upload failed with a visible reason. |

No sector may invent incompatible status names without updating this document and recording a memory entry.

## 5. MVP media output contract

The initial output format is HLS.

Required output layout:

```txt
processed/{video_id}/hls/
  master.m3u8
  720p/
    playlist.m3u8
    segment_000.ts or segment_000.m4s
    ...
  360p/
    playlist.m3u8
    segment_000.ts or segment_000.m4s
    ...
  thumbnail.jpg
```

Minimum renditions:

| Rendition | Target |
|---|---|
| 720p | Primary high quality MVP rendition. |
| 360p | Low bandwidth MVP rendition. |

If source resolution is lower than a target rendition, the worker should skip impossible upscale-heavy renditions unless a sector decision explicitly says otherwise.

Default codec target:

```txt
Video: H.264
Audio: AAC
Container/packaging: HLS-compatible MPEG-TS or fragmented MP4
```

## 6. Canonical data model

The exact schema may evolve, but the following domain objects are required.

### `users`

- `id`
- `email`
- `clerk_user_id`
- `created_at`

### `videos`

- `id`
- `owner_id`
- `title`
- `description`
- `privacy`, default `private`
- `status`
- `original_storage_key`
- `hls_master_storage_key`
- `thumbnail_storage_key`
- `duration_seconds`
- `width`
- `height`
- `video_codec`
- `audio_codec`
- `source_bitrate`
- `failure_code`
- `failure_message`
- `created_at`
- `updated_at`

### `video_renditions`

- `id`
- `video_id`
- `label`, for example `720p`
- `width`
- `height`
- `target_bitrate`
- `playlist_storage_key`
- `status`
- `created_at`

### `video_processing_jobs`

- `id`
- `video_id`
- `status`
- `attempt_count`
- `worker_id`
- `started_at`
- `finished_at`
- `error_code`
- `error_message`
- `created_at`

### `playback_events`

MVP optional for the first vertical slice, but strongly preferred for learning player observability once playback works.

- `id`
- `user_id`
- `video_id`
- `event_type`
- `position_seconds`
- `quality_label`
- `client_timestamp`
- `created_at`

## 7. API contract shape

Exact endpoint names may vary, but the MVP must expose equivalent capabilities.

```txt
GET    /me

POST   /videos
GET    /videos
GET    /videos/{video_id}
PATCH  /videos/{video_id}
DELETE /videos/{video_id}

POST   /videos/{video_id}/upload
POST   /videos/{video_id}/process
GET    /videos/{video_id}/processing-status

GET    /videos/{video_id}/playback
GET    /videos/{video_id}/hls/{path}
POST   /videos/{video_id}/events

GET    /admin/jobs
GET    /admin/videos/{video_id}/debug
```

Authentication is provided by Clerk. The API must verify Clerk-issued identity/session tokens and must not implement custom password storage for MVP.

The frontend must not guess filesystem paths or MinIO bucket/object paths. It should ask the API for playback information.

## 8. MVP interface decisions

These decisions are binding MVP defaults.

### 8.1 Privacy default

Ready videos default to `private`.

Minimum privacy values:

```txt
private, public, unlisted
```

MVP behavior:

- `draft`, `uploading`, `uploaded`, `queued`, `probing`, `processing`, and `failed` videos are owner-only.
- New videos are created with `privacy = private`.
- `ready` videos remain owner-only unless the owner explicitly changes privacy.
- `public` videos may be viewed by anyone.
- `unlisted` videos may be viewed by anyone with the link, but are excluded from public listing/search surfaces.
- Paid/subscriber access is out of scope.

### 8.2 Upload transport

The MVP upload path is API-mediated:

```txt
browser -> FastAPI upload endpoint -> MinIO original object
```

Required behavior:

- FastAPI performs auth, ownership checks, size limits, media validation, and status transitions.
- FastAPI writes the original object to MinIO using controlled storage keys.
- Successful upload transitions to `uploaded`, then enqueues Celery and transitions to `queued` when the job is created.
- Presigned direct-to-MinIO uploads are explicitly deferred until the API-mediated path works end to end.

### 8.3 Playback delivery

The MVP playback path is an authenticated API proxy:

```txt
browser/hls.js -> FastAPI playback/HLS route -> MinIO processed object
```

Required behavior:

- `GET /videos/{video_id}/playback` returns API-owned playback URLs, not raw bucket paths.
- HLS playlist and segment requests are served through an allowlisted route such as `GET /videos/{video_id}/hls/{path}`.
- The route validates video readiness, privacy, and ownership/access before serving objects from `processed/{video_id}/hls/`.
- Path traversal and arbitrary bucket access must be prevented.
- CDN or presigned-MinIO delivery can replace the proxy later without changing the worker output layout.

## 9. Security baseline

MVP security is basic but non-negotiable.

- Users can only mutate their own videos.
- Users can only see private/unpublished videos they own.
- Uploads must enforce file size limits.
- Uploads must validate expected media type and extension but must not trust either alone.
- API must not expose arbitrary local filesystem paths.
- API must not expose raw MinIO bucket internals as stable public API.
- Worker must process files from controlled storage paths only.
- Path traversal must be prevented.
- Processing errors must be sanitized before returning to users.
- Secrets must come from environment variables, not committed files.

## 10. Definition of Done for the MVP

The MVP is done when a clean checkout can do this:

```txt
1. Start the stack using documented local commands.
2. Log in as a Clerk-backed user.
3. Upload a small sample MP4.
4. See the video transition through queued/processing states.
5. Worker generates HLS output and a thumbnail.
6. Video reaches ready state.
7. Watch page plays the HLS stream through the API playback/HLS route in a browser.
8. API prevents one user from editing another user's video.
9. A failed/bad upload produces a visible failed state and useful logs.
10. Critical tests and smoke checks pass.
11. Every sector involved has written a memory entry.
```

## 11. Memory / minimal changelog protocol

Every sector agent must write a minimal changelog / ADR-style entry under the root `memory/` folder before handing off work.

Filename format:

```txt
memory/DDMMYY-SECTOR-short-topic.md
```

Examples:

```txt
memory/280626-B-video-status-schema.md
memory/280626-D-hls-transcode-worker.md
memory/280626-E-hls-player-events.md
```

Required entry format:

```md
# DDMMYY-SECTOR-short-topic

Sector: <A-H sector name>
Agent: <agent name or identifier>
Date: <DD-MM-YYYY>
Branch/Commit: <branch and/or commit hash if known>

## What changed
- <minimal bullets>

## Decisions / ADR notes
- Decision: <architecture or interface decision>
- Reason: <why>
- Alternatives considered: <brief, optional>

## Validation
- <commands/tests/manual checks run>

## Files touched
- <important files only>

## Handoff / risks
- <what the next agent needs to know>
```

Rules:

- Keep entries short and searchable.
- One entry per meaningful sector handoff.
- Do not overwrite another sector's entry.
- If no architecture decision was made, write `No ADR-level decision.` under `Decisions / ADR notes`.
- If validation was not run, explicitly write `Not run` and explain why.

## 12. Required agent grounding rule

Before editing implementation code, every agent must:

1. Read this file.
2. Read `docs/01-agent-operating-contract.md`.
3. Read its sector manifest under `docs/sectors/`.
4. Inspect current repository code before making changes.
5. Check the latest official docs for the framework/tool it is touching when behavior, APIs, or commands may have changed.
6. Keep work inside MVP scope unless explicitly asked by the human owner.
7. Write a `memory/` entry before handoff.

Useful official reference anchors:

- Apple HTTP Live Streaming documentation: https://developer.apple.com/documentation/http-live-streaming
- Apple HLS overview: https://developer.apple.com/streaming/
- FFmpeg documentation: https://ffmpeg.org/documentation.html
- ffprobe documentation: https://ffmpeg.org/ffprobe.html
- hls.js repository/docs: https://github.com/video-dev/hls.js/
- Media Source Extensions overview: https://developer.mozilla.org/en-US/docs/Web/API/Media_Source_Extensions_API

## 13. Remaining owner decisions

The stack, ready-video default privacy, upload transport, and playback delivery strategy are now resolved for the MVP. Remaining decisions should not block the first vertical slice.

1. Maximum local upload size for the MVP.
2. Exact monorepo shape, with `apps/web`, `apps/api`, `workers/media`, `packages/shared`, `infra/docker`, and `fixtures/media` still recommended unless implementation reveals a simpler fit.
3. Whether playback events are required in the first demo or can follow immediately after basic playback.
