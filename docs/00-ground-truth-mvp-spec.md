# Ground Truth MVP Spec — Learning Streaming Platform

Status: canonical planning document  
Audience: all sector agents and the human engineering owner  
Last updated: 28-06-2026

## 1. Mission

Build a from-scratch, self-hostable video-on-demand streaming platform for learning purposes.

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
- Local-first storage with a clean path to object storage later.
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

## 3. Architecture assumptions

The default stack for the MVP is:

| Layer | Default choice | Rationale |
|---|---|---|
| Frontend | Next.js or React | Fast product iteration, simple watch/upload pages |
| API | FastAPI or Express/NestJS | Clean HTTP contracts and easy file/job orchestration |
| Database | PostgreSQL | Durable relational state and predictable querying |
| Queue | Redis-backed queue: Celery/RQ/BullMQ | Simple background processing |
| Worker | FFmpeg + ffprobe | Direct exposure to media processing fundamentals |
| Storage | Local filesystem first; MinIO/S3-compatible later | Simpler MVP, clean migration path |
| Delivery | Static file serving/Nginx first; CDN later | HLS files are static HTTP assets |
| Player | hls.js or equivalent | Browser HLS playback with MSE support |
| Local orchestration | Docker Compose | Repeatable dev environment |

Agents may propose alternatives only if they preserve the MVP loop and record the decision in `memory/`.

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
- `password_hash` or external auth identity
- `created_at`

### `videos`

- `id`
- `owner_id`
- `title`
- `description`
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

MVP optional but strongly preferred for learning player observability.

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
POST   /auth/register
POST   /auth/login
GET    /me

POST   /videos
GET    /videos
GET    /videos/{video_id}
PATCH  /videos/{video_id}
DELETE /videos/{video_id}

POST   /videos/{video_id}/upload
POST   /videos/{video_id}/complete-upload
POST   /videos/{video_id}/process
GET    /videos/{video_id}/processing-status

GET    /videos/{video_id}/playback
POST   /videos/{video_id}/events

GET    /admin/jobs
GET    /admin/videos/{video_id}/debug
```

The frontend must not guess filesystem paths. It should ask the API for playback information.

## 8. Security baseline

MVP security is basic but non-negotiable.

- Users can only mutate their own videos.
- Users can only see private/unpublished videos they own.
- Uploads must enforce file size limits.
- Uploads must validate expected media type and extension but must not trust either alone.
- API must not expose arbitrary local filesystem paths.
- Worker must process files from controlled storage paths only.
- Path traversal must be prevented.
- Processing errors must be sanitized before returning to users.
- Secrets must come from environment variables, not committed files.

## 9. Definition of Done for the MVP

The MVP is done when a clean checkout can do this:

```txt
1. Start the stack using documented local commands.
2. Create or log in as a user.
3. Upload a small sample MP4.
4. See the video transition through queued/processing states.
5. Worker generates HLS output and a thumbnail.
6. Video reaches ready state.
7. Watch page plays the HLS stream in a browser.
8. API prevents one user from editing another user's video.
9. A failed/bad upload produces a visible failed state and useful logs.
10. Critical tests and smoke checks pass.
11. Every sector involved has written a memory entry.
```

## 10. Memory / minimal changelog protocol

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

## 11. Required agent grounding rule

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

## 12. Open questions for the human owner

These should be resolved when convenient, but they do not block MVP planning.

1. Preferred app stack: Python/FastAPI or TypeScript/Node for the backend?
2. Preferred frontend: Next.js full-stack app or separate React SPA?
3. Do you want local filesystem only for the first build, or MinIO from day one?
4. Should authentication be custom email/password or outsourced to a provider later?
5. What maximum upload size should the MVP support locally?
6. Should the MVP support public videos only, or private videos from day one?
7. Should the MVP repo be monorepo with `apps/web`, `apps/api`, `workers/media`, or simpler flat structure?
