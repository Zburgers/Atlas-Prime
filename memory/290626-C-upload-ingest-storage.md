# 290626-C-upload-ingest-storage

Sector: C upload, ingest, and storage
Agent: Codex
Date: 29-06-2026
Branch/Commit: main / uncommitted

## What changed
- Added API-mediated `POST /videos/{video_id}/upload` for browser -> FastAPI -> MinIO original uploads.
- Added MinIO storage and Celery enqueue service boundaries.
- Added upload validation for owner access, size, extension, content type, empty files, and lightweight container headers.
- Added API tests for unauthorized upload, invalid media, oversized media, and successful upload/job queueing.

## Decisions / ADR notes
- Decision: Store originals at `originals/{video_id}/source.{ext}` and enqueue `media_worker.process_video` with `video_id`, `job_id`, and `original_storage_key`.
- Reason: Matches the Sector C MVP default and gives Sector D a stable worker payload without exposing MinIO credentials to browsers.
- Alternatives considered: Browser direct-to-MinIO presigned uploads, deferred by the MVP spec.

## Validation
- `pytest` from `apps/api` (17 passed)
- `make lint`
- `make test`
- `make smoke`
- `docker compose run --rm api alembic upgrade head`
- Live API smoke: created a video, uploaded `fixtures/media/sample-2s.mp4`, received `video_status=queued`, `job_status=queued`, and verified MinIO object `originals/fbe6b340-bbc7-4abc-a8c7-fa62c522a8fa/source.mp4`.

## Files touched
- apps/api/app/api/videos.py
- apps/api/app/services/storage.py
- apps/api/app/services/uploads.py
- apps/api/app/services/processing_queue.py
- apps/api/tests/test_video_api.py
- workers/media/media_worker/celery_app.py
- docs/api-database.md
- docs/local-dev.md
- compose.yaml
- .env.example

## Handoff / risks
- Sector D must replace the placeholder `media_worker.process_video` task with real ffprobe/FFmpeg processing and DB job updates.
- API upload currently buffers each accepted file through a spooled temp file before MinIO upload; this is acceptable for the 100 MiB MVP default but should be revisited before larger uploads.
- Unrelated `apps/web/` and `package-lock.json` changes were present at handoff and were not included in this Sector C commit.
