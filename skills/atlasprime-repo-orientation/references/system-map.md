# AtlasPrime system map

This map is a fast orientation aid for the repository. It was inspected on 2026-08-24 at branch `docs/fullplatform-rollout`, `HEAD` `6ee3323` (`feat: add telemetry retention purge`). Recheck `git status`, `git log`, and the code before relying on any snapshot detail.

At inspection time the worktree also contained an unrelated, untracked `apps/api/app/services/telemetry_metrics.py`. Tracked analytics and API code imports it, so a fresh agent must preserve the file and determine whether the active implementation is intentionally being completed before running or judging broad validation. It is not part of this onboarding commit.

## First five minutes

```sh
git status --short --branch
git log -1 --oneline --decorate
sed -n '1,180p' docs/plans/README.md
sed -n '1,220p' docs/local-dev.md
docker compose config -q
```

Canonical reading and authority:

1. [`docs/00-ground-truth-mvp-spec.md`](../../../docs/00-ground-truth-mvp-spec.md) — approved MVP scope, stack, privacy defaults, video lifecycle, HLS contract.
2. [`docs/PRODUCT_SPEC_AND_ENGINEERING_HANDBOOK.md`](../../../docs/PRODUCT_SPEC_AND_ENGINEERING_HANDBOOK.md) — reconciled product, architecture, evidence, risks, and drift.
3. [`docs/plans/README.md`](../../../docs/plans/README.md) — current sequential execution index; the only live plan queue.
4. [`docs/sectors/`](../../../docs/sectors/) — narrow interface contracts for sectors A–H.
5. [`memory/`](../../../memory/) — dated handoffs and decisions; historical evidence must be checked against code and branch state.

## Runtime topology

Local orchestration is defined by [`compose.yaml`](../../../compose.yaml). `make up` creates `.env` from `.env.example` when absent and starts the stack.

| Unit | Entry point / image | Responsibility | Local exposure and dependencies |
|---|---|---|---|
| `web` | Next.js app from `apps/web/Dockerfile` | Browser UI, Clerk client, same-origin backend proxy | Host `3001` → container `3000`; waits for API health |
| `api` | `app.main:app` from `apps/api/Dockerfile` | FastAPI HTTP contracts, auth, domain services, storage and Celery dispatch | Host `8000`; waits for Postgres, Redis, search, MinIO bootstrap |
| `postgres` | `postgres:16-alpine` | Durable relational state and Alembic schema | Host `15432`; persistent `postgres-data` volume |
| `redis` | `redis:7-alpine` | Celery broker/result backend and telemetry admission/metrics counters | Host `16379`; no persistent volume in Compose |
| `search` | Meilisearch `v1.37` | Search index and health dependency when `ATLAS_SEARCH_BACKEND=meilisearch` | Host `7700`; persistent `meilisearch-data` volume |
| `minio` | MinIO | Private original and processed object storage | API `9000`, console `9001`; persistent `minio-data` volume |
| `minio-bootstrap` | MinIO `mc` one-shot | Creates private `atlas-originals` and `atlas-processed` buckets | Must complete before API/worker |
| `worker` | `media_worker.celery_app:celery_app` | Media queue, ffprobe/FFmpeg processing, HLS packaging and publication | Queue `media`; waits for API, DB, Redis, MinIO |
| `analytics-worker` | `app.worker.analytics` Celery worker | Daily analytics rebuild and raw telemetry retention purge | Queue `analytics` |
| `search-worker` | `app.worker.search` Celery worker | Rebuilds the public-ready search corpus | Queue `search`; waits for Meilisearch |
| `analytics-beat` | `app.worker.analytics` Celery beat | Schedules recent analytics rebuild and telemetry purge | Depends on analytics worker |
| `web-test` | Web builder image, test profile | Runs the Node web tests/lint/build commands | Only used by `make test`/`make lint` or Compose test profile |

The intended trust path is browser → Next `/api/backend` proxy → FastAPI → PostgreSQL/Redis/MinIO/Meilisearch; FastAPI → Celery/Redis → media or analytics/search worker. MinIO buckets remain private.

## Application entry points

### FastAPI

`apps/api/app/main.py` constructs the application, request IDs, health checks, and router registration. It exposes:

- `GET /healthz/live` — unauthenticated liveness.
- `GET /healthz` — Postgres, Redis, MinIO, and optional Meilisearch dependency checks.
- `GET /dev/mvp-contract` — local/smoke contract introspection; not a product API.

Routers are registered in `main.py` from `apps/api/app/api/`. The route groups are:

| Area | Entry points |
|---|---|
| Identity and core videos | `GET /me`; `POST/GET /videos`; `GET/PATCH/DELETE /videos/{video_id}`; `GET /videos/{video_id}/related` |
| Upload and processing | `POST /videos/{video_id}/upload`; `POST /videos/{video_id}/process`; `GET /videos/{video_id}/processing-status` |
| Playback and telemetry | `GET /videos/{video_id}/playback`; `GET /videos/{video_id}/hls/{asset_path}`; `GET /videos/{video_id}/delivery/{asset_path}`; `POST /videos/{video_id}/events`; `POST /videos/{video_id}/impressions`; `POST /videos/{video_id}/views` |
| Engagement | `GET /videos/{video_id}/engagement`; `POST/DELETE /videos/{video_id}/like`; `POST/DELETE /videos/{video_id}/watch-later` |
| Discovery | `GET /search`; `GET /feed/home`; `GET /feed/trending`; `GET /feed/subscriptions`; `GET /feed/requests/{request_id}/debug` |
| Channels and subscriptions | `GET/PATCH /channels/me`; `GET /channels/{handle}`; `POST/DELETE /channels/{channel_id}/subscribe` |
| History | `GET /library/history` |
| Comments and moderation | `GET/POST /videos/{video_id}/comments`; `DELETE /comments/{comment_id}`; `POST /moderation/reports`; admin report queue/action/audit routes under `/admin/reports` and `/admin/audit-log` |
| Playlists | `POST /playlists`; `GET /playlists/{playlist_id}`; `POST/DELETE /playlists/{playlist_id}/items/...` |
| Creator Studio | `/studio/videos`; `/studio/videos/{video_id}` metadata/retry/timeline/token-rotation/chapter routes; caption and thumbnail routes under `/studio/videos/{video_id}`; `GET /studio/analytics` |
| Admin and operations | `/admin/ops`; `/admin/telemetry`; `/admin/videos`; `/admin/jobs`; `/admin/videos/{video_id}/debug`; recommendation/search debug and reindex routes; analytics rebuild |

Exact decorator-level routes are in the files under `apps/api/app/api/`; do not add a competing route table to docs when changing one.

### Next.js web

`apps/web/app/` uses the App Router. `apps/web/proxy.ts` installs Clerk middleware. `apps/web/app/api/backend/[...path]/route.ts` forwards `GET`, `POST`, `PATCH`, and `DELETE` requests to `ATLAS_API_BASE_URL` (container default `http://api:8000`) while retaining the browser's same-origin path and query.

| Browser surface | Main implementation and connected system |
|---|---|
| `/` | Home/library discovery shell |
| `/upload` | `upload/upload-form.tsx`; create video, multipart upload, poll processing, link to watch |
| `/watch/[videoId]` | `watch/watch-client.tsx`; metadata/status/playback, hls.js/native fallback, views, playback telemetry, likes, watch-later, comments, related videos |
| `/library` | Authenticated watch history |
| `/search` | Search query and result cards |
| `/trending` and `/subscriptions` | Feed and subscribed-channel lists |
| `/channels/[handle]` | Public channel and its videos |
| `/playlists/new` and `/playlists/[playlistId]` | Playlist creation and playback list |
| `/studio`, `/studio/videos`, `/studio/videos/[videoId]` | Creator metadata, retry/status timeline, chapters, captions, thumbnails |
| `/studio/analytics` | Creator analytics dashboard |
| `/admin` and `/admin/reports` | Operator dashboard/report actions; API remains the authorization authority |
| `/sign-in` and `/sign-up` | Clerk auth surfaces |

Shared frontend transport/types live in `apps/web/app/components/video-api.ts`. `apiRequest()` calls `/api/backend`; `backendAssetUrl()` ensures playback assets stay API-owned rather than exposing MinIO paths.

## Functioning systems and where to follow them

### 1. Upload → process → HLS playback

The complete MVP loop is split across these boundaries:

1. `apps/web/app/upload/upload-form.tsx` creates a private draft with `POST /videos` and sends the file to `POST /videos/{id}/upload`.
2. `apps/api/app/services/uploads.py` validates filename, extension, size, and container header; claims an upload generation; writes the original through `apps/api/app/services/storage.py`; and enqueues the worker payload through `processing_queue.py`.
3. The payload is exactly `video_id`, `job_id`, `generation`, and `original_storage_key` for `media_worker.process_video`.
4. `workers/media/media_worker/celery_app.py` downloads the original, probes it, packages HLS, uploads an attempt-scoped tree, and uses `repository.py` to fence status/publication updates.
5. `workers/media/media_worker/packager.py` owns ffprobe parsing, rendition planning, FFmpeg HLS output, master playlist, and thumbnail generation. It skips impossible upscale-heavy renditions.
6. `apps/api/app/api/videos.py` and `services/videos.py` enforce ready/privacy/access checks. Playback is served through API HLS or signed-delivery routes and is bound to the published `video_asset_inventory`.
7. `watch-client.tsx` loads API playback metadata and feeds the master playlist to hls.js, with browser-native HLS fallback.

Canonical video statuses are `draft → uploading → uploaded → queued → probing → processing → ready`, with `failed` as the visible failure terminal/retry state. Privacy is `private`, `public`, or `unlisted`; new videos default private, and non-ready videos remain owner-only.

### 2. Generation fencing, publication, and deletion

- `videos.active_processing_generation` and `video_processing_jobs.generation` identify the authoritative processing attempt.
- Only one queued/running job per video is allowed by the database partial uniqueness rule.
- Attempt assets are staged below `processed/{video_id}/attempts/{generation}/hls/`.
- The worker writes typed `video_asset_inventory` rows and atomically publishes job, rendition, thumbnail, and video state only when job/video/generation/status/tombstone predicates still match.
- Playback only serves paths in the active published generation inventory; stale or legacy paths fail closed.
- Delete is tombstone-first: active jobs are canceled, storage cleanup is claimed separately, and `make deletion-reconcile` retries pending/running/failed cleanup.
- `make processing-recover-stale` is explicit and dry-run by default. `ARGS="--apply"` is required to fail matching stale jobs; it does not auto-enqueue retries.

Follow [`docs/runbooks/processing-publication-deletion.md`](../../../docs/runbooks/processing-publication-deletion.md) before touching these interfaces.

### 3. Auth, ownership, and privacy

- Clerk is the external identity provider. `apps/web/proxy.ts` supplies frontend middleware; API auth is in `apps/api/app/services/auth.py` and `app/api/deps.py`.
- Accepted API identity sources are a Clerk bearer token or `__session` cookie. Development identity headers are accepted only when `ATLAS_ALLOW_DEV_AUTH_HEADERS=true`.
- Token verification checks RS256 signature, issuer, required time/subject claims, pending status, and configured authorized party (`azp`).
- `get_video_for_owner()` protects mutations; `get_video_for_read()` protects metadata/status; playback helpers additionally require ready state and privacy rules.
- `ATLAS_ADMIN_CLERK_USER_IDS` is the current operator allowlist used by `AdminUserDep`; the admin UI itself is not a separate authorization boundary.

### 4. Discovery, search, and ranking

- `services/feed.py` and `domain/ranking.py` produce home, trending, subscriptions, and related-video feeds; `recommendation_logging.py` records request/result evidence.
- `api/search.py`, `services/search.py`, and `services/search_index.py` provide PostgreSQL search and Meilisearch-backed search/read fallback.
- `workers/search.py` rebuilds the public-ready corpus on the `search` queue; `make search-reindex` enqueues a complete rebuild.
- Captions are normalized into search documents by `services/captions.py`/search indexing and can return a plain-text caption snippet.
- Public discovery must remain limited to ready, public, approved, non-deleted videos. Unlisted videos are link-readable but excluded from public browse/search.

### 5. Creator and community systems

- Channels: `services/channels.py`, `api/channels.py`, `/channels/[handle]`; default channel creation is coupled to user/video ownership.
- Engagement: `services/reactions.py`, video engagement routes, and watch client like/watch-later controls.
- History/subscriptions: `services/subscriptions.py`, `api/library.py`, `/library`, `/subscriptions`.
- Playlists: `services/playlists.py`, `api/playlists.py`, `/playlists/*`.
- Comments: `services/comments.py`, `api/comments.py`, watch-page comment UI.
- Moderation: `services/moderation.py`, report/action/audit routes, and `/admin/reports`.
- These are implemented post-MVP slices on this branch; do not broaden them or assume their presence changes the locked MVP boundaries.

### 6. Studio and media assets

- Studio video listing/update/retry/timeline/token rotation/chapters live in `api/studio.py` and `services/studio.py`/`chapters.py`.
- Captions use `api/captions.py` and `services/captions.py`; uploads are validated WebVTT/text-track inputs.
- Thumbnails use `api/thumbnails.py` and `services/thumbnails.py`; worker-generated and creator-uploaded thumbnails share API-selected delivery semantics.
- Analytics uses `api/studio_analytics.py`, `services/analytics.py`, and `worker/analytics.py`; `make analytics-rebuild DATE_FROM=... DATE_TO=...` runs the explicit rebuild command.

### 7. Telemetry and operational visibility

- Playback events are posted by the watch client to `/videos/{id}/events`, deduplicated by client `event_id`, scoped by `playback_session_id`, and admitted through Redis in `services/telemetry_admission.py`.
- Raw playback events are retained for 30 days by `services/telemetry_retention.py`, `purge_telemetry`, and the scheduled analytics worker task. The command is dry-run by default; `--apply` is destructive.
- `services/telemetry_metrics.py` is an in-flight worktree dependency at this snapshot and supplies aggregate Redis counters read by `/admin/telemetry`; inspect its current diff before relying on this path.
- `api/admin.py` exposes health/queue/video/job/debug/telemetry views. `ProcessingQueue` wraps Celery worker and queue inspection.
- Logs should retain `video_id`, `job_id`, and sector/stage context without secrets, raw tokens, or absolute filesystem paths.

## Data and storage contracts

### Database

`apps/api/app/db/models.py` is the ORM map; `apps/api/alembic/versions/` is the migration authority. Major tables include:

- `users`, `channels`, and `channel_subscriptions` for identity and creator surfaces.
- `videos`, `video_renditions`, `video_processing_jobs`, `video_asset_inventory` for lifecycle/media state.
- `playback_events`, `video_impressions`, `video_views`, `daily_video_metrics` for telemetry/analytics.
- `video_reactions`, `video_saves`, `watch_history`, and `subscriptions` for engagement/history.
- `video_comments`, moderation reports/actions/audit rows, recommendation logs/results, playlists/items, thumbnails, text tracks, and chapters for post-MVP surfaces.

The canonical status enums and transition graph are in `apps/api/app/domain/status.py`. Do not invent a new status string in a route, worker, migration, or UI.

### Object storage

The buckets are private and configured through environment variables. The API mediates originals and playback; the browser must not know MinIO bucket/object internals.

- Originals: controlled keys under the original storage abstraction.
- Published HLS: attempt-scoped processed objects under `processed/{video_id}/attempts/{generation}/hls/`.
- Database inventory stores HLS-root-relative path, content type, size, and SHA-256 for the published generation.
- The original MVP output contract is `master.m3u8`, `720p/`, `360p/`, and `thumbnail.jpg`; current worker output and inventory are the final code contract.

### Configuration

Read `.env.example`, `compose.yaml`, `apps/api/app/core/config.py`, and `workers/media/media_worker/config.py` together. The important groups are database/Redis/Celery, Clerk, MinIO buckets/endpoints, playback mode/token, Meilisearch, upload limits, stale recovery, and worker concurrency. Never copy real values into docs, tests, commits, or agent output.

## Validation and safe operator entry points

| Command | Use | Caution |
|---|---|---|
| `make env` | Create local `.env` if absent | Does not configure real Clerk credentials |
| `make up` / `make down` / `make ps` / `make logs` | Start, stop, inspect, and follow Compose | Check existing services/ports first; do not stop unrelated stacks |
| `make db-upgrade` | Apply Alembic migrations | Changes local DB state; confirm this is intended |
| `make test` | API, media worker, and web tests in containers | Builds/runs services; preserve active worktree |
| `make worker-test` | Media worker tests only | Useful for packager/repository changes |
| `make lint` | Compose config, Python compileall, web lint | Current target is syntax/config plus web lint, not a full release gate |
| `make smoke` | Full local upload → process → playback smoke | Use `WEB_PORT=3002 WEB_SMOKE_URL=http://127.0.0.1:3002 make smoke` if 3001 is occupied; never kill an unrelated listener |
| `make fixture` | Generate ignored sample MP4 | Writes `fixtures/media/sample-2s.mp4` |
| `make search-reindex` | Enqueue public search index rebuild | Requires running search worker |
| `make analytics-rebuild DATE_FROM=... DATE_TO=...` | Rebuild daily aggregates | Explicit date range required |
| `make telemetry-purge` | Dry-run raw-event retention report | `ARGS="--apply"` deletes eligible rows; review first |
| `make processing-recover-stale` | Dry-run stale job candidates | `ARGS="--apply"` mutates matching job state; no automatic retry |
| `make deletion-reconcile` | Apply pending/failed tombstone cleanup | Storage and DB side effects; use only when requested |

Focused tests are in `apps/api/tests/`, `workers/media/tests/`, and `apps/web/tests/`. CI is `.github/workflows/ci.yml`; historical green results are evidence for their exact SHA only.

## Common traps

- The current branch is ahead of `main` and the plan ledger is branch-specific. Refresh remote refs before making merge/release claims.
- `docs/plans/02-fullplatform-vision.md` is architecture/reference, not the task queue.
- `make smoke` can fail solely because host port `3001` is occupied; use an alternate web port and preserve the unrelated process.
- A successful unit test or health endpoint does not prove authenticated browser behavior, deployed identity, production readiness, or live worker/recovery concurrency.
- Normal product responses should not expose storage keys or Celery identifiers; use protected admin/debug contracts when needed.
- Do not make MinIO buckets public, add direct browser uploads, or bypass the API playback proxy without an explicit owner-approved contract change.
- Do not use `git reset --hard`, `git clean`, broad deletion, or a worktree cleanup while another implementation is in progress.
