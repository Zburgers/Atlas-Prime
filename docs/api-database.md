# API and Database Contract

Status: Sector B/F foundation plus media publication/deletion contracts reconciled
Last updated: 24-08-2026

## Database Access

- SQLAlchemy async ORM is the application database boundary.
- `app.db.session.get_session` yields one `AsyncSession` per request.
- Service functions own commits for MVP route operations; callers should not keep ORM objects across requests.
- Alembic owns schema evolution. Run `make db-upgrade` after starting Postgres or before using video routes on a clean database.
- `DATABASE_URL` may use `postgresql://` in Compose env files; the API and Alembic convert it to `postgresql+asyncpg://`.

## Domain Tables

- `users` stores Clerk identity with `clerk_user_id`; no password fields exist.
- `videos` stores owner, privacy, canonical lifecycle status, media metadata, storage keys, failure fields, and the nullable `active_processing_generation` UUID for the current upload/processing generation.
- `video_renditions` stores one row per generated HLS rendition.
- `video_asset_inventory` stores the committed generated HLS manifest for each published generation, including relative path, content type, byte size, and SHA-256.
- `video_processing_jobs` stores durable worker job attempts, each with a non-null `generation` UUID. A partial unique index permits at most one `queued` or `running` job per video.
- `playback_events` is present for later player observability.

## Route Boundaries

- Sector B implements metadata CRUD, processing status, job records, playback metadata shape, and admin query skeletons.
- Sector C owns upload completion and original object writes.
- Sector D owns worker job execution and rendition population.
- Sector E owns the real HLS object proxy behind `GET /videos/{video_id}/hls/{path}`.
- Sector F replaced the default identity boundary with Clerk session JWT verification.

## Auth and Access Control

- Protected API requests accept a Clerk session token from `Authorization: Bearer <token>` or the Clerk `__session` cookie.
- The operator identity source for this deployment is the comma-separated `ATLAS_ADMIN_CLERK_USER_IDS` environment allowlist. `AdminUserDep` performs the server-side membership check; a signed-in frontend account is not an operator grant.
- `GET /me`, video mutations, processing enqueue, and admin routes require a valid Clerk identity.
- `GET /videos`, `GET /videos/{video_id}`, processing status, playback metadata, and HLS proxy authorization allow anonymous requests only for `ready` videos with `public` or `unlisted` privacy.
- Draft/uploading/uploaded/queued/probing/processing/failed videos remain owner-only regardless of privacy.
- A tombstoned video is missing from all normal creator/public reads and mutations, including listing, detail, processing status, playback, upload, process, update, and delete lookup. The tombstone row remains available to protected operator/debug surfaces.
- Development identity headers are disabled by default. Set `ATLAS_ALLOW_DEV_AUTH_HEADERS=true` only for local smoke/tests that intentionally use `X-Atlas-Dev-Clerk-User-Id`.

## Product and operator response schemas

Normal public and creator routes use product schemas (`VideoResponse`, `VideoListItemResponse`, `RenditionResponse`, and `VideoUploadResponse`). These contain domain state and API-owned delivery URLs only; they do not expose MinIO object keys or Celery task identifiers. This applies to create, list, detail, upload, status, and playback responses.

Protected operator routes use explicit debug schemas (`VideoDebugResponse`, `RenditionDebugResponse`, and `AdminVideoDebugResponse`). They may expose storage-backed keys and processing diagnostics for `/admin/videos` and `/admin/videos/{video_id}/debug` only, and every admin route is protected by `AdminUserDep`.

The Next.js backend proxy forwards the caller's Clerk credentials and remains a transport boundary. FastAPI is authoritative for operator authorization, response redaction, and 403 behavior; proxy access must not be treated as an independent role grant.

## Upload and Storage Contract

- `POST /videos/{video_id}/upload` accepts multipart form data with a `file` field and requires the authenticated owner.
- The MVP transport is browser -> FastAPI -> MinIO. Browser clients do not need MinIO credentials or bucket names.
- FastAPI validates extension, content type, lightweight container header, empty file, and `ATLAS_UPLOAD_MAX_BYTES` before storing the original.
- Supported original containers for the first upload path are `mp4`, `m4v`, `mov`, and `webm`.
- Originals are stored in the private originals bucket using `originals/{video_id}/source.{ext}`.
- A successful upload atomically claims `draft` or `failed` as `uploading`, assigns `videos.active_processing_generation`, stores `videos.original_storage_key`, creates a matching `video_processing_jobs.generation`, transitions the video to `queued`, and enqueues Celery task `media_worker.process_video`.
- Invalid uploads transition the owned video to `failed` with a sanitized failure code/message. Cross-user uploads are rejected before storage.

## Media publication and deletion contract

- Generated HLS assets are immutable and attempt-scoped:
  `processed/{video_id}/attempts/{generation}/hls/{relative_path}`. The current worker never writes the legacy `processed/{video_id}/hls/` prefix, and inventory-bound playback rejects legacy publication keys.
- The worker upload interface returns a typed record for every uploaded asset: storage key, HLS-rooted relative path, content type, byte size, and SHA-256 checksum. Upload failure cleanup is limited to the matching video/generation attempt prefix.
- Publication is a single fenced synchronous psycopg transaction. It validates a complete master, rendition playlist and segment manifest plus `thumbnail.jpg`, inserts the generation's `video_asset_inventory` rows, replaces generated rendition/thumbnail rows, and advances the matching job/video state. The fence matches video, job, generation, and active generation and requires `deleted_at IS NULL` with `deletion_status = 'complete'`; any later fence failure rolls back every publication mutation. The previous published attempt is deleted only after commit.
- `videos.hls_master_storage_key` identifies the committed published attempt. Playback derives the published generation from that strict key and authorizes each requested relative path by inventory membership before any storage read. Valid-but-uninventoried, stale-generation, and legacy paths are 404; traversal and malformed paths remain 400.
- `DELETE /videos/{video_id}` is asynchronous. The owner transaction locks the row, records `deleted_at`, sets `deletion_status = 'pending'`, clears `active_processing_generation`, fences queued/running work, and returns 202 before external storage I/O. Fresh-session cleanup removes the original and `processed/{video_id}/` objects through storage abstractions, then marks the tombstone complete and clears stale storage pointers. Failures preserve retryable keys/state with a sanitized `deletion_error`; `make deletion-reconcile` retries pending, running, and failed tombstones without clearing `deleted_at` or resurrecting content.

## Processing Generation and Queue Contract

- `videos.active_processing_generation` is the authoritative generation for the current upload and processing attempt. The job row and queue message must carry the same UUID.
- Upload claim and active-job uniqueness prevent concurrent upload requests from creating divergent active jobs. A stale or redelivered worker cannot claim, stage, succeed, or fail a different generation: worker updates are conditional on the matching `video_id`, `job_id`, `generation`, expected job status, and `videos.active_processing_generation`. Fence loss is a no-op with transaction rollback.
- The exact Celery keyword payload is:

  ```json
  {
    "video_id": "<video UUID>",
    "job_id": "<processing job UUID>",
    "generation": "<processing generation UUID>",
    "original_storage_key": "originals/<video_id>/source.<ext>"
  }
  ```

- Stale recovery is explicit and bounded. `ATLAS_PROCESSING_STALE_SECONDS` defaults to `900` seconds and has a minimum of `60`. `make processing-recover-stale` performs a dry run by default; use `ARGS="--apply"` for the explicit operator action.
- Recovery considers only running jobs with an old `started_at`. Apply mode conditionally fails the matching job and video only when `video_id`, `generation`, running/status state, and the captured `started_at` still match. Stale recovery never retries automatically and never enqueues a replacement job.
