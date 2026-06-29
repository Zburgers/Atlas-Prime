# 290626-D-hls-worker-packaging

Sector: D media processing and HLS packaging
Agent: Codex
Date: 29-06-2026
Branch/Commit: main / uncommitted

## What changed
- Replaced the placeholder `media_worker.process_video` task with MinIO download, ffprobe metadata extraction, FFmpeg HLS packaging, thumbnail generation, processed-object upload, and DB job/video/rendition updates.
- Added deterministic HLS output under `processed/{video_id}/hls/` with master playlist, rendition playlist/segments, and thumbnail.
- Added repeatable worker tests and wired them into `make test`, `make worker-test`, and `make lint`.

## Decisions / ADR notes
- Decision: Skip 720p output when the source is below 1280x720; do not upscale the MVP fixture.
- Reason: Matches the Sector D and ground-truth spec rule to avoid generating renditions larger than source media unless explicitly decided.
- Alternatives considered: Always pad/upscale to 720p, rejected as out of spec for MVP.

## Validation
- `PYTHONPATH=workers/media pytest workers/media/tests` (2 passed)
- `docker compose run --rm --build worker pytest tests` (2 passed)
- `docker compose run --rm --build api pytest` (17 passed)
- `make worker-test`
- `make lint`
- `make test`
- `make smoke`
- Live smoke: API upload of `fixtures/media/sample-2s.mp4` queued job `5a6d7f79-e0ea-46d9-80cf-b31d9b9dcbcc`; worker marked video `f6916128-f3c8-428f-aad8-84eddf0ca02c` ready, wrote metadata, one `360p` rendition, `master.m3u8`, `thumbnail.jpg`, and `segment_000.ts` to MinIO.

## Files touched
- workers/media/media_worker/celery_app.py
- workers/media/media_worker/config.py
- workers/media/media_worker/packager.py
- workers/media/media_worker/repository.py
- workers/media/media_worker/storage.py
- workers/media/tests/test_packager.py
- workers/media/Dockerfile
- workers/media/requirements.txt
- compose.yaml
- Makefile

## Handoff / risks
- Sector E still owns replacing the API `GET /videos/{video_id}/hls/{path}` 501 placeholder with the authenticated MinIO-backed HLS proxy.
- A 640x360 source currently produces only `360p`; sources at or above 1280x720 produce both `720p` and `360p`.
