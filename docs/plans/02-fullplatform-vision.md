# Atlas Prime Full Platform Rollout Implementation Plan

> For future implementation agents: execute this plan phase by phase, and keep using the repo's required read set, sector manifests, validation gates, and memory handoff protocol before each work unit.

**Goal:** Evolve the completed Atlas Prime MVP into a self-hostable, YouTube-like VOD platform with public discovery, creator tooling, analytics, moderation, search, recommendations, and production-grade media delivery.

**Architecture:** Keep the current Next.js + FastAPI + PostgreSQL + Redis/Celery + MinIO + FFmpeg + hls.js backbone. Grow the platform through explicit domain modules, staged schema additions, measured event collection, and promotion gates instead of rewriting the stack or jumping straight to ML/CDN complexity.

**Tech Stack:** Next.js App Router, React, Clerk, FastAPI, SQLAlchemy ORM, Alembic, PostgreSQL, Redis, Celery, MinIO/S3-compatible object storage, FFmpeg/ffprobe, HLS, hls.js, Docker Compose.

---

## 0. How To Use This Document

This is the post-MVP rollout contract. It does not replace:

- `docs/00-ground-truth-mvp-spec.md` for the completed MVP contract.
- `docs/01-agent-operating-contract.md` for agent behavior.
- `docs/sectors/*.md` for the current A-H sector ownership model.
- `memory/` for factual handoff entries.

Use this document when planning work beyond the existing MVP loop. Every phase below must keep the current MVP loop working:

```txt
sign in
  -> create video
  -> upload through FastAPI
  -> store original in MinIO
  -> queue Celery job
  -> ffprobe/FFmpeg package HLS
  -> store processed HLS in MinIO
  -> serve playback through API-owned HLS routes
  -> play with hls.js
  -> record playback/admin debug data
```

If a future task wants live streaming, DRM, ads, payments, mobile apps, or ML recommendations, it must first prove the earlier gates in this document.

## 1. Executive Direction

Atlas Prime should become a serious video platform, not only an upload demo.

The product target:

```txt
creators upload and manage videos
  -> media is processed, thumbnailed, indexed, and monitored
  -> viewers discover videos through home, search, channels, playlists, and feeds
  -> the player emits useful events
  -> analytics, search, and recommendations use those events
  -> admins can operate moderation, jobs, storage, and abuse workflows
```

Strategic rules:

- Do not rewrite the MVP stack. It is the foundation.
- Do not repurpose existing sector names. A-H already mean product shell, API/data, upload/storage, media worker, playback delivery, auth, observability/admin, and devex/testing.
- Do not make MinIO object paths a public product contract. The API owns playback URLs and access checks.
- Do not build ML before event quality, public content inventory, search, and deterministic ranking exist.
- Do not build CDN/direct upload until auth, privacy, and API-owned control remain intact.
- Do not add monetization before abuse controls, metrics, and moderation workflows exist.

## 2. Current Baseline Verified From The Repo

Current branch for this planning pass:

```txt
docs/fullplatform-rollout
```

Current primary files:

```txt
compose.yaml
Makefile
.env.example
.github/workflows/ci.yml
scripts/smoke-devex.sh
apps/web/
apps/api/
workers/media/
docs/
memory/
```

The current local stack is:

```txt
postgres
redis
minio
minio-bootstrap
api
worker
web
web-test
```

The current baseline is not empty. It already has:

- Next.js App Router frontend under `apps/web`.
- FastAPI backend under `apps/api`.
- SQLAlchemy models and Alembic migration for users, videos, renditions, jobs, and playback events.
- Clerk-backed auth verification plus local dev auth headers for smoke tests.
- API-mediated uploads through `POST /videos/{video_id}/upload`.
- Controlled original storage keys under `originals/{video_id}/source.{ext}`.
- Celery task `media_worker.process_video`.
- FFmpeg/ffprobe media worker under `workers/media`.
- Processed HLS output under `processed/{video_id}/hls/`.
- API-owned playback metadata at `GET /videos/{video_id}/playback`.
- API-owned HLS assets at `GET /videos/{video_id}/hls/{asset_path}`.
- Path traversal protection before processed-object reads.
- hls.js browser playback in `apps/web/app/watch/[videoId]/watch-client.tsx`.
- Playback event ingestion at `POST /videos/{video_id}/events`.
- Admin status/debug endpoints under `/admin`.
- Full-stack smoke coverage in `scripts/smoke-devex.sh`.

Current canonical statuses:

```txt
draft
uploading
uploaded
queued
probing
processing
ready
failed
```

Current privacy values:

```txt
private
public
unlisted
```

Current validation commands:

```sh
make lint
make test
make smoke
```

For docs-only work, at minimum run:

```sh
git diff --check
```

## 3. Reference Docs Checked For This Planning Pass

Latest official references checked on 2026-07-02:

- Next.js App Router docs: https://nextjs.org/docs/app
- Clerk Next.js quickstart: https://clerk.com/docs/nextjs/getting-started/quickstart
- Clerk manual JWT verification: https://clerk.com/docs/guides/sessions/manual-jwt-verification
- FastAPI docs: https://fastapi.tiangolo.com/
- SQLAlchemy ORM docs: https://docs.sqlalchemy.org/en/20/orm/
- Alembic docs: https://alembic.sqlalchemy.org/en/latest/
- Celery docs: https://docs.celeryq.dev/en/stable/
- MinIO Python/developer docs: https://docs.min.io/aistor/developers/
- hls.js docs/repo: https://github.com/video-dev/hls.js/
- Apple HLS docs: https://developer.apple.com/documentation/http-live-streaming
- FFmpeg docs: https://ffmpeg.org/documentation.html
- Docker Compose docs: https://docs.docker.com/compose/
- YouTube recommendation architecture paper: https://research.google.com/pubs/archive/45530.pdf
- TensorFlow Recommenders docs: https://www.tensorflow.org/recommenders

Notes from the docs check:

- The web app is on Next `16.2.9`; the Next docs page reported latest `16.2.10`. Treat this as a patch-level upgrade candidate, not a blocker for platform planning.
- The current App Router layout, route handlers, proxy, and client-component split are compatible with the product direction.
- Clerk's manual JWT guidance still supports JWKS-backed verification, which matches the current FastAPI auth approach.
- Docker Compose health-gated startup remains the right local orchestration model for this repo.

## 4. Non-Negotiable Architecture Invariants

### 4.1 Ownership And Privacy

- New videos default to `private`.
- Non-ready videos remain owner-only regardless of privacy value.
- Private ready videos are owner/admin only.
- Public ready videos are eligible for browse, search, channel pages, and recommendations.
- Unlisted ready videos are playable by link but excluded from public browse/search/recommendation surfaces.
- Removed or moderation-limited videos must not leak through public listing endpoints.

### 4.2 API-Owned Media Control

- The frontend asks the API for playback metadata.
- The frontend never constructs MinIO bucket names or storage keys.
- The worker may write deterministic object keys, but those keys are not the public product API.
- Any future signed URL/CDN path must preserve API access checks before the browser receives a playable URL.

### 4.3 Status Separation

Do not overload `videos.status`.

Keep separate:

- Media lifecycle: `draft`, `uploading`, `uploaded`, `queued`, `probing`, `processing`, `ready`, `failed`.
- Privacy: `private`, `public`, `unlisted`.
- Moderation: `pending`, `approved`, `limited`, `removed`, `rejected`.
- Job status: `queued`, `running`, `succeeded`, `failed`, `canceled`.
- Asset/rendition status: `pending`, `processing`, `ready`, `failed`.

### 4.4 Event Quality Before Algorithms

Recommendations, trending, analytics, and search ranking depend on reliable events. Build the event model before ranking complexity.

Minimum useful event spine:

```txt
impression
card_click
player_ready
play
pause
seek
progress_ping
buffer_start
buffer_end
quality_change
ended
like
save
comment
share
not_interested
report
```

Every feed/search/recommendation response should eventually include:

```txt
request_id
surface
algorithm_version
rank
reason/debug metadata for internal/admin use
```

### 4.5 Modular Monolith First

Keep one FastAPI app and one PostgreSQL database until the domain boundaries are clearer. Add modules before services.

Good next boundary:

```txt
apps/api/app/
  api/
    videos.py
    admin.py
    channels.py
    feed.py
    search.py
    comments.py
    playlists.py
    studio.py
    moderation.py
  services/
    videos.py
    uploads.py
    storage.py
    processing_queue.py
    playback.py
    channels.py
    feed.py
    search.py
    analytics.py
    recommendations.py
    moderation.py
  schemas/
    videos.py
    channels.py
    feed.py
    search.py
    comments.py
    playlists.py
    moderation.py
  domain/
    status.py
    privacy.py
    moderation.py
    ranking.py
    events.py
```

Split into services only when operational pressure justifies it.

## 5. Target Product Surfaces

### Viewer

```txt
/
/watch/[videoId]
/search
/@[handle]
/feed/subscriptions
/feed/trending
/library
/playlists/[playlistId]
```

Viewer capabilities:

- Browse public ready videos.
- Search public videos.
- Watch public, unlisted, or owned private videos.
- See channel identity and related videos.
- Like/save/watch later.
- Comment and report.
- View watch history and subscriptions.

### Creator

```txt
/upload
/studio
/studio/videos
/studio/videos/[videoId]
/studio/analytics
/studio/comments
```

Creator capabilities:

- Create draft-first uploads.
- Track processing timeline.
- Edit title, description, tags, category, privacy, scheduled publish time.
- Manage thumbnails and captions.
- Retry failed processing.
- See analytics and retention.
- Moderate comments on own videos.

### Admin/Ops

```txt
/admin
/admin/ops
/admin/videos
/admin/jobs
/admin/reports
/admin/moderation
```

Admin capabilities:

- Inspect API, worker, queue, database, and storage health.
- See failed jobs and HLS asset state.
- Inspect a video debug timeline.
- Review reports and moderation actions.
- Remove/restore/limit content.
- Audit admin decisions.

## 6. Core Request Flows

### 6.1 Existing Upload And Processing Flow

```txt
Next.js upload form
  -> POST /videos
  -> POST /videos/{video_id}/upload
  -> FastAPI validates auth, owner, size, extension, content type, and file signature
  -> MinIO originals bucket
  -> video status uploaded/queued
  -> Celery media_worker.process_video
  -> worker downloads original
  -> ffprobe metadata
  -> FFmpeg HLS renditions + thumbnail
  -> MinIO processed bucket
  -> DB marks ready or failed
```

Keep this path working in every phase.

### 6.2 Existing Playback Flow

```txt
Watch page
  -> GET /videos/{video_id}
  -> GET /videos/{video_id}/processing-status
  -> GET /videos/{video_id}/playback
  -> hls.js loads /api/backend/videos/{video_id}/hls/master.m3u8
  -> Next route proxy forwards to FastAPI
  -> FastAPI validates readiness/privacy/path
  -> FastAPI reads processed object from MinIO
  -> browser plays HLS
  -> POST /videos/{video_id}/events
```

Future signed/CDN delivery must preserve the same authorization decision before bytes are served.

### 6.3 Public Feed Flow

```txt
GET /feed/home
  -> identify optional user
  -> filter public ready videos
  -> exclude removed/limited/hidden
  -> rank by deterministic v1 score
  -> attach request_id, surface, rank, reason
  -> return video cards with API-owned thumbnail URLs
  -> client posts impression events
```

### 6.4 Search Flow

```txt
metadata change or video ready
  -> enqueue search indexing job
  -> build search document
  -> index in Postgres FTS first
  -> later index in search service

GET /search?q=...
  -> parse query
  -> search public ready approved videos
  -> rank lexical relevance + freshness + engagement
  -> return request_id and result rank
  -> client posts impressions/clicks
```

### 6.5 Analytics Flow

```txt
client event
  -> POST /events or /videos/{id}/events
  -> validate accessible target and event shape
  -> write raw event
  -> async aggregate worker
  -> update daily metrics and feature snapshots
  -> Creator Studio/Admin read aggregate tables
```

### 6.6 Recommendation Flow

```txt
request feed/watch-next
  -> call candidate generators
  -> merge and dedupe candidates
  -> apply access/moderation filters
  -> rank with algorithm version
  -> log request/results
  -> return cards and request_id
  -> impressions/clicks/watch events join back to request_id
```

## 7. Data Architecture

### 7.1 Current Tables

Already present:

```txt
users
videos
video_renditions
video_processing_jobs
playback_events
```

### 7.2 Phase 1 Tables

Add public platform basics:

```txt
channels
  id
  owner_user_id
  handle
  display_name
  description
  avatar_storage_key
  banner_storage_key
  created_at
  updated_at

video_tags
  video_id
  tag
  created_at

video_thumbnails
  id
  video_id
  storage_key
  source
  frame_time_seconds
  width
  height
  selected
  created_at

video_reactions
  id
  user_id
  video_id
  reaction_type
  created_at

video_impressions
  id
  user_id
  video_id
  surface
  request_id
  position
  shown_at
```

Rules:

- `channels.handle` must be unique, normalized, and reserved-word checked.
- A user should get exactly one default channel in Phase 1.
- One selected thumbnail per video.
- Reactions need uniqueness on `(user_id, video_id, reaction_type)` or a stricter per-user reaction rule.

### 7.3 Phase 2 Tables

Add engagement and creator workflows:

```txt
channel_subscriptions
playlists
playlist_items
comments
comment_reactions
comment_reports
video_saves
watch_history
video_text_tracks
video_chapters
```

### 7.4 Phase 3 Tables

Add analytics/search/recommendation infrastructure:

```txt
video_interactions
recommendation_requests
recommendation_results
search_queries
search_results
video_daily_metrics
creator_daily_metrics
channel_daily_metrics
user_video_features
video_feature_snapshots
```

### 7.5 Phase 4+ Tables

Add platform maturity:

```txt
content_reports
moderation_actions
audit_log_entries
notifications
notification_preferences
experiments
experiment_assignments
storage_lifecycle_events
asset_delivery_tokens
```

Monetization tables are deliberately excluded until trust, analytics, and moderation are stable.

## 8. API Rollout

### 8.1 Current API Baseline

Current routes already include:

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
GET    /videos/{video_id}/hls/{asset_path}
POST   /videos/{video_id}/events
GET    /admin/ops
GET    /admin/videos
GET    /admin/jobs
GET    /admin/videos/{video_id}/debug
GET    /healthz
GET    /healthz/live
GET    /dev/mvp-contract
```

### 8.2 Phase 1 API Additions

```txt
GET    /feed/home
GET    /channels/{handle}
PATCH  /channels/me
GET    /channels/{handle}/videos
GET    /search
POST   /videos/{video_id}/like
DELETE /videos/{video_id}/like
POST   /videos/{video_id}/impressions
GET    /studio/videos
PATCH  /studio/videos/{video_id}
```

### 8.3 Phase 2 API Additions

```txt
POST   /channels/{channel_id}/subscribe
DELETE /channels/{channel_id}/subscribe
GET    /feed/subscriptions
GET    /feed/trending
POST   /videos/{video_id}/watch-later
DELETE /videos/{video_id}/watch-later
GET    /videos/{video_id}/comments
POST   /videos/{video_id}/comments
POST   /comments/{comment_id}/reply
DELETE /comments/{comment_id}
POST   /playlists
GET    /playlists/{playlist_id}
POST   /playlists/{playlist_id}/items
DELETE /playlists/{playlist_id}/items/{item_id}
```

### 8.4 Phase 3 API Additions

```txt
GET    /videos/{video_id}/related
GET    /studio/analytics
GET    /admin/search
GET    /admin/recommendations
POST   /events
```

Use `POST /events` only after a generic event schema exists. Until then, keep playback-scoped events under `/videos/{video_id}/events`.

### 8.5 Phase 4+ API Additions

```txt
GET    /admin/reports
POST   /admin/moderation/actions
GET    /notifications
PATCH  /notifications/{notification_id}
POST   /studio/videos/{video_id}/captions
POST   /studio/videos/{video_id}/thumbnails
POST   /studio/videos/{video_id}/retry-processing
POST   /studio/videos/{video_id}/publish
```

## 9. Frontend Rollout

### 9.1 Current Frontend Baseline

Current routes:

```txt
/
/upload
/watch/[videoId]
/admin
/sign-in
/sign-up
```

Current key files:

```txt
apps/web/app/page.tsx
apps/web/app/components/video-list.tsx
apps/web/app/components/video-api.ts
apps/web/app/upload/upload-form.tsx
apps/web/app/watch/[videoId]/watch-client.tsx
apps/web/app/admin/admin-dashboard.tsx
apps/web/app/api/backend/[...path]/route.ts
```

### 9.2 Target Routes By Phase

Phase 1:

```txt
/
/search
/@[handle]
/studio
/studio/videos
```

Phase 2:

```txt
/feed/subscriptions
/feed/trending
/library
/playlists/[playlistId]
/studio/videos/[videoId]
```

Phase 3:

```txt
/studio/analytics
/studio/comments
/admin/reports
/admin/moderation
```

### 9.3 Component System

Add reusable product components as features land:

```txt
VideoCard
VideoGrid
VideoShelf
VideoPlayer
ChannelAvatar
ChannelHeader
SubscribeButton
EngagementBar
CommentThread
SearchBox
SearchFilters
UploadDropzone
ProcessingTimeline
ThumbnailPicker
AnalyticsChart
RecommendationSidebar
AdminMetricTile
ModerationQueue
```

Design direction:

- Thumbnail-first, card/grid browsing for public surfaces.
- Dense operational tables for Studio/Admin.
- Clear separation between Viewer, Studio, and Admin navigation.
- No public listing of private, failed, draft, or processing content.
- No visible raw storage keys in user-facing UI.
- Mobile responsive from the first public feed work.

## 10. Media And Delivery Roadmap

### 10.1 Current Worker Contract

Current worker responsibilities:

- Download original from MinIO.
- Probe media with `ffprobe`.
- Generate HLS with FFmpeg.
- Generate `thumbnail.jpg`.
- Upload processed tree to MinIO.
- Update video/job/rendition records.
- Mark success or sanitized failure.

Current rendition ladder:

```txt
720p: 2.8 Mbps
360p: 800 Kbps
fallback: source-height rendition if source is smaller
```

### 10.2 Media Phase M1

Improve quality without changing architecture:

- Add `480p` and `1080p` where source allows.
- Store per-rendition codec, bitrate, segment count, and output size.
- Store multiple generated thumbnails.
- Add deterministic retry/reprocess behavior.
- Add processing stage metadata to jobs.
- Add cleanup of partial processed objects on failure.

Do not upscale by default.

### 10.3 Media Phase M2

Add creator controls:

- Custom thumbnail upload.
- Caption track upload (`.vtt`, `.srt` converted to `.vtt`).
- Chapter metadata.
- Reprocess button.
- Processing timeline.

### 10.4 Delivery Phase D1

Keep API proxy but harden:

- Preserve private-by-default access checks.
- Add Range support only if the player path needs it.
- Keep segment cache headers immutable.
- Add request IDs to HLS access logs.
- Track HLS asset misses separately from auth denials.

### 10.5 Delivery Phase D2

Move bytes off the API only after access semantics are proven:

```txt
GET /videos/{id}/playback
  -> API validates viewer
  -> API returns short-lived signed URLs or signed CDN cookie
  -> browser fetches playlists/segments from CDN/object origin
```

Acceptance for D2:

- Private video cannot be fetched by another user.
- Token expiry works.
- Public/unlisted rules match API proxy behavior.
- Worker output layout remains unchanged.
- API can revoke or rotate playback tokens.

## 11. Search, Recommendations, And Analytics

### 11.1 Search Phases

S0 - PostgreSQL search:

- Full-text search over title, description, channel display name, and tags.
- Public ready approved videos only.
- Rank by text relevance, freshness, and basic engagement.

S1 - Dedicated search service:

- Add Meilisearch, Typesense, OpenSearch, or Tantivy after Postgres search proves product value.
- Add async indexing worker.
- Add admin index health and reindex command.

S2 - Transcript search:

- Index captions/transcripts.
- Return matching transcript snippets.

S3 - Hybrid search:

- Combine lexical relevance, semantic vector similarity, engagement quality, freshness, and personalization.

### 11.2 Recommendation Phases

R0 - Deterministic home feed:

```txt
score =
  freshness * 0.35
  + log(views + 1) * 0.25
  + log(likes + 1) * 0.15
  + completion_rate * 0.25
  - penalties
```

R1 - Related videos:

- Same channel.
- Shared tags/category.
- Title/description similarity.
- Exclude already watched and moderation-limited content.

R2 - Personalized feed:

- Use watch history, subscriptions, liked videos, and negative feedback.
- Keep deterministic formula and debug reasons.

R3 - Candidate generation plus ranking:

- Candidate sources: popular, fresh, subscribed, similar-to-history, same-topic, collaborative signals.
- Ranker combines candidates and logs algorithm version.

R4 - ML retrieval/ranking:

- Train offline first.
- Use embeddings only after event data is clean.
- Require offline evaluation and A/B experiment guardrails.

### 11.3 Recommendation Safety Rules

- Do not optimize only for clicks.
- Include report and not-interested penalties.
- Cap repeated same-channel exposure.
- Track creator diversity.
- Track new-creator exposure.
- Keep algorithm versions visible in admin/debug surfaces.

## 12. Security, Privacy, And Trust

### 12.1 Access Matrix

```txt
draft/uploading/uploaded/queued/probing/processing/failed:
  owner/admin only

ready + private:
  owner/admin only

ready + unlisted:
  anyone with link, excluded from public discovery

ready + public:
  browse/search/feed/watch eligible

removed:
  admin only

limited:
  watchable only if policy permits, excluded from recommendation/search by default
```

### 12.2 Security Additions

Add in phases:

- Rate limits for upload, comment, search, event ingestion, and auth-heavy routes.
- Upload quotas per user/channel.
- Storage quotas per user/channel.
- Admin role separation.
- Audit logs for moderation/admin actions.
- CSRF posture review for state-changing web flows.
- Event privacy rules.
- Account/content deletion and export later.

### 12.3 Moderation Data Model

```txt
content_reports
  id
  reporter_user_id
  target_type
  target_id
  reason
  details
  status
  created_at

moderation_actions
  id
  actor_user_id
  target_type
  target_id
  action
  reason
  created_at

audit_log_entries
  id
  actor_user_id
  action
  target_type
  target_id
  metadata_json
  created_at
```

## 13. Infrastructure And Operations

### 13.1 Current Local Infra

Keep the current Compose stack as the local truth:

```txt
compose.yaml
Makefile
.env.example
scripts/smoke-devex.sh
```

Do not replace this with Kubernetes for the next phases.

### 13.2 Next Compose Additions

Add only when the owning feature needs them:

```txt
search
event-worker
analytics-worker
recommendation-worker
scheduler
mailhog
prometheus
grafana
loki
```

Each service addition must include:

- `.env.example` entries.
- Compose healthcheck or readiness strategy.
- `make` command or documented invocation.
- Smoke or targeted verification.
- Memory entry documenting cross-sector impact.

### 13.3 Production Shape

Initial production-like shape:

```txt
web: Next.js
api: FastAPI
worker-media: Celery media workers
worker-events: async event aggregation
postgres: durable relational store
redis: broker/cache
object storage: MinIO/S3-compatible
search: dedicated service after S1
cdn: after Delivery D2
```

The first production deployment should still be single-region and understandable.

### 13.4 Observability

Add:

- Request IDs on API requests.
- Playback session IDs.
- Recommendation request IDs.
- Structured logs for upload, worker, playback, search, feed, moderation.
- Metrics for queue depth, job duration, failures, HLS misses, upload failures, event ingestion errors.
- Admin dashboard panels for those metrics.

## 14. Validation Gates

### 14.1 Always Green

Every phase must preserve:

```sh
make lint
make test
make smoke
```

For docs-only changes:

```sh
git diff --check
```

### 14.2 Feature Gate

Each feature issue must include at least:

- Unit tests for business rules.
- API tests for auth/privacy.
- Migration upgrade from clean DB if schema changes.
- Frontend smoke or component-level test if UI changes.
- `make smoke` if upload/playback/auth/public listing is touched.
- Memory entry before handoff.

### 14.3 Phase Promotion Gate

A phase is complete only when:

- All acceptance criteria pass on a clean stack.
- Docs and `memory/` explain new contracts.
- No known private content leak exists.
- New endpoints have ownership/privacy tests.
- Admin/debug views exist for new async workflows.
- Owner has a clear next phase recommendation.

## 15. Phased Rollout

### Phase 0 - Stabilize Current MVP

Status: baseline already exists; keep it green.

Goal: make the current upload/process/playback loop boringly reliable.

Required evidence:

```sh
make lint
make test
make smoke
```

Acceptance:

- Clean stack starts.
- Known-good MP4 reaches `ready`.
- Bad MP4 reaches `failed`.
- Owner can play private ready video.
- Other user cannot mutate or play private video.
- HLS assets are fetched only through API-owned paths.

### Phase 1 - Public Platform Basics

Goal: make Atlas Prime feel like a small public VOD site.

Build:

- Public home video card grid.
- Channel model and default channel creation.
- Channel page.
- API-owned thumbnail URLs on cards.
- View/impression event foundation.
- Like/unlike.
- Search v1 with PostgreSQL full-text search.
- Basic Studio video manager.

Acceptance:

- Signed-out viewer sees only public ready videos.
- Signed-in creator still sees private drafts in Studio/library.
- Public cards show thumbnail, duration, title, channel, views, age.
- Channel page lists public ready channel videos.
- Search respects privacy/unlisted rules.
- Basic view/like counts are shown without leaking private content.

### Phase 2 - Engagement And Creator Workflow

Goal: make viewers and creators return.

Build:

- Comments v1.
- Watch later.
- Playlists.
- Subscriptions feed.
- Watch history.
- Studio video detail editor.
- Custom thumbnail upload.
- Captions upload.
- Processing retry/timeline.

Acceptance:

- Viewer can comment, save, subscribe, and manage watch later.
- Creator can edit metadata, thumbnail, captions, and publish state.
- Creator can retry failed processing.
- Private video comments remain private.
- Studio separates own content from public browsing.

### Phase 3 - Discovery, Analytics, And Deterministic Ranking

Goal: make discovery measurable and debuggable.

Build:

- Home feed v1 ranking.
- Watch-next related videos.
- Trending feed.
- Rich playback progress events.
- Impression/click/request logging.
- Analytics aggregation worker.
- Creator analytics dashboard.
- Admin recommendation/search debug views.

Acceptance:

- Feed response includes request ID and algorithm version.
- Impressions join to clicks/playback events.
- Creator sees views, watch time, average view duration, and top videos.
- Admin can inspect feed/search/recommendation health.
- Ranking code is deterministic and tested.

### Phase 4 - Media And Delivery Upgrade

Goal: make media quality and delivery scale past the local MVP proxy.

Build:

- Expanded rendition ladder.
- Per-rendition metadata.
- Multiple thumbnails.
- Caption packaging/serving.
- Worker retry/idempotency.
- Signed playback URLs or signed CDN delivery.
- Storage lifecycle cleanup.

Acceptance:

- 1080p/480p are generated when source allows.
- Source is not upscaled by default.
- Failed reprocesses are safe and visible.
- CDN/object delivery preserves private/unlisted/public access rules.
- API bandwidth is no longer required for segment bytes in production mode.

### Phase 5 - Search Service And Recommendation V2

Goal: move from deterministic discovery to scalable retrieval/ranking.

Build:

- Dedicated search service.
- Search indexing worker.
- Transcript indexing.
- Candidate generators.
- Recommendation request/result logs.
- User/video feature snapshots.
- Offline ranking evaluation.

Acceptance:

- Search indexes asynchronously and has reindex tooling.
- Home/watch-next use multiple candidate sources.
- Algorithm version is logged for each recommendation request.
- Offline metrics exist before online experiment rollout.

### Phase 6 - ML Personalization

Goal: add ML only after the event platform is trustworthy.

Build:

- Embedding generation.
- Retrieval model.
- Ranking model.
- Feature store tables.
- Experiment assignment.
- Guardrail metrics.

Acceptance:

- Offline model can produce candidates.
- Ranker can be versioned and rolled back.
- A/B experiments compare algorithm versions.
- Report/not-interested/safety guardrails are enforced.

### Phase 7 - Trust, Notifications, Monetization, And Advanced Platform

Goal: mature into a real platform.

Build:

- Moderation queue and audit trail.
- Abuse detection.
- Copyright/takedown workflow.
- Notifications.
- Email.
- Monetization primitives only after trust and metrics.
- PWA/mobile polish.
- Shorts/live streaming only after VOD maturity.

Acceptance:

- Admin can process reports and audit actions.
- Notifications are preference-controlled.
- Monetization has fraud, payout, tax, and abuse prerequisites documented.

## 16. First Issues To Write

### Issue 1 - Public Video Card Grid

Status: implemented on branch `docs/fullplatform-rollout`; keep this issue's acceptance checks as regression criteria.

Files:

- Modify: `apps/api/app/services/videos.py`
- Modify: `apps/api/app/api/videos.py`
- Modify: `apps/web/app/page.tsx`
- Modify: `apps/web/app/components/video-list.tsx`
- Test: `apps/api/tests/test_video_api.py`
- Test: `apps/web/tests/smoke.test.js`

Steps:

1. Add/verify API listing filter for public ready videos for signed-out users.
2. Return card-safe fields: title, thumbnail URL, duration, privacy, status, created age.
3. Replace the private library-style home with a public video grid.
4. Keep signed-in upload/creator entry visible.
5. Test private/processing videos are excluded from signed-out listing.
6. Run `make test`.

Acceptance:

- Public visitor sees only public ready videos.
- Private and non-ready videos are not leaked.
- Card links to watch page.
- Thumbnail URL is API-owned.

### Issue 2 - Channel Model

Status: implemented on branch `docs/fullplatform-rollout`; keep this issue's acceptance checks as regression criteria.

Files:

- Create: `apps/api/alembic/versions/<timestamp>_channels.py`
- Modify: `apps/api/app/db/models.py`
- Create: `apps/api/app/api/channels.py`
- Create: `apps/api/app/services/channels.py`
- Create: `apps/api/app/schemas/channels.py`
- Modify: `apps/api/app/main.py`
- Test: `apps/api/tests/test_channels.py`

Steps:

1. Add `channels` table with unique normalized handle.
2. Create or fetch default channel for a Clerk user.
3. Add `GET /channels/{handle}` and `PATCH /channels/me`.
4. Associate videos to a channel or derive channel from owner for v1.
5. Test handle uniqueness and public channel read.
6. Run migration and API tests.

Acceptance:

- New users get or can create a channel.
- Channel handle is stable and unique.
- Channel page can list public ready videos.

### Issue 3 - View Counts And Impressions

Status: implemented on branch `docs/fullplatform-rollout`; keep this issue's acceptance checks as regression criteria.

Files:

- Create: `apps/api/alembic/versions/<timestamp>_impressions_and_views.py`
- Modify: `apps/api/app/db/models.py`
- Create: `apps/api/app/domain/events.py`
- Create: `apps/api/app/services/analytics.py`
- Modify: `apps/api/app/api/videos.py`
- Modify: `apps/api/app/schemas/videos.py`
- Modify: `apps/web/app/components/video-api.ts`
- Modify: `apps/web/app/components/video-list.tsx`
- Modify: `apps/web/app/channels/[handle]/channel-client.tsx`
- Modify: `apps/web/app/watch/[videoId]/watch-client.tsx`
- Test: `apps/api/tests/test_analytics_events.py`

Steps:

1. Add `video_impressions` and normalized view event support.
2. Define view threshold so refreshes do not overcount.
3. Record impression positions from public grids/feed.
4. Show view count on cards.
5. Test duplicate view suppression.
6. Run `make test`.

Acceptance:

- View count increments only after a valid threshold.
- Impression events include surface, position, and request ID when present.

### Issue 4 - Search V1

Status: implemented on branch `docs/fullplatform-rollout`; keep this issue's acceptance checks as regression criteria.

Files:

- Create: `apps/api/app/api/search.py`
- Create: `apps/api/app/services/search.py`
- Create: `apps/api/app/schemas/search.py`
- Modify: `apps/api/app/main.py`
- Modify: `apps/web/app/components/app-header.tsx`
- Modify: `apps/web/app/components/video-api.ts`
- Create: `apps/web/app/search/page.tsx`
- Create: `apps/web/app/search/search-client.tsx`
- Test: `apps/api/tests/test_search.py`

Steps:

1. Add Postgres full-text search over title/description/channel.
2. Filter to public ready videos.
3. Add `/search?q=...`.
4. Add search page and header search box.
5. Test privacy and ranking basics.
6. Run `make test`.

Acceptance:

- Search returns public ready videos only.
- Search ranks obvious title matches first.
- Empty query and no-result states are handled.

### Issue 5 - Likes And Watch Later

Status: implemented on branch `docs/fullplatform-rollout`; keep this issue's acceptance checks as regression criteria.

Files:

- Create: `apps/api/alembic/versions/<timestamp>_video_reactions_saves.py`
- Modify: `apps/api/app/db/models.py`
- Create: `apps/api/app/services/reactions.py`
- Modify: `apps/api/app/api/videos.py`
- Modify: `apps/api/app/schemas/videos.py`
- Modify: `apps/web/app/components/video-api.ts`
- Modify: `apps/web/app/components/video-list.tsx`
- Modify: `apps/web/app/watch/[videoId]/watch-client.tsx`
- Test: `apps/api/tests/test_reactions.py`

Steps:

1. Add `video_reactions` and `video_saves`.
2. Add like/unlike endpoints.
3. Add watch-later save/remove endpoints.
4. Add watch-page engagement controls.
5. Test auth, idempotency, and privacy.
6. Run `make test`.

Acceptance:

- Signed-in viewer can like/unlike once.
- Signed-in viewer can save/remove watch later.
- Public counts do not expose private videos.

### Issue 6 - Creator Studio Video Manager

Status: implemented on branch `docs/fullplatform-rollout`; keep this issue's acceptance checks as regression criteria.

Files:

- Create: `apps/api/app/api/studio.py`
- Create: `apps/api/app/services/studio.py`
- Create: `apps/api/app/schemas/studio.py`
- Modify: `apps/api/app/main.py`
- Modify: `apps/web/app/components/app-header.tsx`
- Modify: `apps/web/app/components/video-api.ts`
- Create: `apps/web/app/studio/page.tsx`
- Create: `apps/web/app/studio/videos/page.tsx`
- Create: `apps/web/app/studio/videos/studio-video-manager.tsx`
- Modify: `apps/web/app/globals.css`
- Test: `apps/api/tests/test_studio.py`

Steps:

1. Add owner-only Studio list endpoint.
2. Add status/privacy filters.
3. Add metadata edit endpoint.
4. Add retry failed processing action only for valid states.
5. Add Studio video table.
6. Test cross-user denial.

Acceptance:

- Creator sees only own videos.
- Creator can edit metadata and privacy.
- Failed video can be retried safely.

### Issue 7 - Comments V1

Status: implemented on branch `docs/fullplatform-rollout`; keep this issue's acceptance checks as regression criteria.

Files:

- Create: `apps/api/alembic/versions/<timestamp>_comments.py`
- Modify: `apps/api/alembic/env.py`
- Modify: `apps/api/app/db/models.py`
- Create: `apps/api/app/api/comments.py`
- Create: `apps/api/app/services/comments.py`
- Create: `apps/api/app/schemas/comments.py`
- Modify: `apps/api/app/main.py`
- Modify: `apps/web/app/components/video-api.ts`
- Modify: `apps/web/app/watch/[videoId]/watch-client.tsx`
- Modify: `apps/web/app/globals.css`
- Test: `apps/api/tests/test_comments.py`

Steps:

1. Add top-level comments.
2. Add list/create/delete endpoints.
3. Enforce video access before listing comments.
4. Allow owner/admin moderation delete later; start with own delete.
5. Add watch-page comment thread.
6. Test private comments are not leaked.

Acceptance:

- Signed-in user can comment on accessible videos.
- Public users can read comments on public videos.
- Private video comments remain private.

### Issue 8 - Feed V1 Ranking

Status: implemented on branch `docs/fullplatform-rollout`; keep this issue's acceptance checks as regression criteria.

Files:

- Create: `apps/api/app/domain/ranking.py`
- Create: `apps/api/app/api/feed.py`
- Create: `apps/api/app/services/feed.py`
- Create: `apps/api/app/schemas/feed.py`
- Modify: `apps/api/app/main.py`
- Modify: `apps/web/app/components/video-api.ts`
- Modify: `apps/web/app/components/video-list.tsx`
- Modify: `apps/web/app/page.tsx`
- Test: `apps/api/tests/test_feed.py`

Steps:

1. Add deterministic ranking function.
2. Add `/feed/home`.
3. Include `request_id`, `surface`, `rank`, and internal reason.
4. Exclude watched/hidden/limited content once those concepts exist.
5. Add home feed UI.
6. Test sorting and filters.

Acceptance:

- Home feed ranks public ready videos by freshness and quality.
- Response includes request ID and algorithm version.
- Ranking function is unit-tested.

### Issue 9 - Recommendation Event Foundation

Status: implemented on branch `docs/fullplatform-rollout`; keep this issue's acceptance checks as regression criteria.

Files:

- Create: `apps/api/alembic/versions/<timestamp>_recommendation_logging.py`
- Modify: `apps/api/app/db/models.py`
- Create: `apps/api/app/services/recommendation_logging.py`
- Modify: `apps/api/app/api/feed.py`
- Test: `apps/api/tests/test_recommendation_logging.py`

Steps:

1. Add `recommendation_requests`.
2. Add `recommendation_results`.
3. Log feed result ranks.
4. Connect impression/click/play events to request ID.
5. Add admin/debug query.
6. Test request/result consistency.

Acceptance:

- Each feed request has a request ID.
- Feed positions can be joined to impressions and playback.

### Issue 10 - Thumbnail Manager

Status: implemented on branch `docs/fullplatform-rollout`; keep this issue's acceptance checks as regression criteria.

Files:

- Create: `apps/api/alembic/versions/<timestamp>_video_thumbnails.py`
- Modify: `apps/api/app/db/models.py`
- Modify: `workers/media/media_worker/packager.py`
- Modify: `workers/media/media_worker/repository.py`
- Create: `apps/api/app/api/thumbnails.py`
- Create: `apps/web/app/studio/videos/[videoId]/page.tsx`
- Test: `workers/media/tests/test_packager.py`
- Test: `apps/api/tests/test_thumbnails.py`

Steps:

1. Store generated thumbnail candidates.
2. Add selected thumbnail invariant.
3. Add custom thumbnail upload.
4. Validate image type/dimensions.
5. Add Studio selector.
6. Test selected thumbnail API URLs.

Acceptance:

- Video has one selected thumbnail.
- Custom thumbnail upload does not expose raw storage keys.

### Issue 11 - Admin Reports And Moderation

Status: implemented on branch `docs/fullplatform-rollout`; keep this issue's acceptance checks as regression criteria.

Files:

- Create: `apps/api/alembic/versions/<timestamp>_moderation.py`
- Modify: `apps/api/app/db/models.py`
- Create: `apps/api/app/api/moderation.py`
- Create: `apps/api/app/services/moderation.py`
- Modify: `apps/api/app/main.py`
- Create: `apps/web/app/admin/reports/page.tsx`
- Test: `apps/api/tests/test_moderation.py`

Steps:

1. Add reports and moderation actions.
2. Add report endpoint for videos/comments.
3. Add admin reports queue.
4. Add remove/restore/limit actions.
5. Add audit log entry on every admin action.
6. Test public surfaces exclude removed content.

Acceptance:

- Users can report content.
- Admin can action reports.
- Moderation actions are auditable.

### Issue 12 - Analytics Aggregates

Status: implemented on branch `docs/fullplatform-rollout`; keep this issue's acceptance checks as regression criteria.

Files:

- Create: `apps/api/alembic/versions/<timestamp>_daily_metrics.py`
- Modify: `apps/api/app/db/models.py`
- Create: `workers/events/` or `apps/api/app/services/analytics.py`
- Create: `apps/api/app/api/studio_analytics.py`
- Create: `apps/web/app/studio/analytics/page.tsx`
- Test: `apps/api/tests/test_analytics_aggregates.py`

Steps:

1. Add daily metrics tables.
2. Implement aggregation command/worker.
3. Add Studio analytics endpoint.
4. Add views/watch-time/top-videos UI.
5. Test aggregate calculation from raw events.
6. Add smoke or command docs.

Acceptance:

- Creator sees basic analytics.
- Aggregates can be rebuilt deterministically from raw events.

## 17. Documentation Architecture

Required docs as the platform grows:

```txt
docs/00-ground-truth-mvp-spec.md
docs/01-agent-operating-contract.md
docs/02-owner-evaluation-and-rollout-guide.md
docs/plans/02-fullplatform-vision.md
docs/local-dev.md
docs/api-database.md
docs/delivery-playback-cdn.md
docs/observability-admin-ops.md
docs/sectors/*.md
memory/*.md
```

Add later when features land:

```txt
docs/architecture/events-and-analytics.md
docs/architecture/search-and-ranking.md
docs/architecture/media-delivery-upgrade.md
docs/architecture/moderation-and-safety.md
docs/runbooks/processing-failures.md
docs/runbooks/search-index-rebuild.md
docs/runbooks/storage-lifecycle.md
```

Documentation rules:

- Specs describe contracts.
- Plans describe implementation order and acceptance.
- Runbooks describe operations/debugging.
- Memory entries describe what actually changed.
- ADR-level decisions belong in memory plus the affected contract doc.

## 18. Immediate Recommended Next Step

Start with Phase 1, Issue 9:

```txt
Recommendation Event Foundation
```

Reason:

- Public browse, channel pages, search, views, impressions, likes, watch-later saves, Creator Studio, comments, and a deterministic home feed are now in place.
- Recommendation event logging is the next durability layer needed to make ranked feed responses auditable.
- It can persist the existing feed `request_id`, rank, and impression/playback join points.
- It does not require new infrastructure.

After Issue 9, do:

```txt
10. Thumbnail Manager
11. Admin Reports And Moderation
12. Analytics Aggregates
```

This order keeps the platform demoable after every increment.

## 19. Explicit Non-Goals For The Next Two Phases

Do not build these in Phase 1 or Phase 2:

```txt
live streaming
DRM
ads
payments
creator payouts
native mobile apps
multi-region deployment
GPU transcoding
copyright fingerprinting
full ML recommender
AI auto-captioning
Shorts clone
direct browser-to-MinIO uploads
CDN delivery as the default playback path
```

They are valid later, but they will distract from turning the working MVP into a coherent platform.

## 20. Final Direction

Atlas Prime should become:

```txt
a self-hostable, professional, YouTube-like VOD platform
with public discovery, channels, search, recommendations,
creator studio, analytics, comments, playlists, moderation,
and production-grade media processing/delivery
```

The current MVP has the right spine. The next transformation is productization:

```txt
from working upload/process/playback loop
to public video platform with measurable discovery and creator operations
```

The winning sequence is:

```txt
public surfaces
  -> channels
  -> events
  -> search
  -> engagement
  -> deterministic feed
  -> analytics
  -> moderation
  -> media/delivery scale
  -> ML recommendations
  -> monetization/live/advanced platform
```
