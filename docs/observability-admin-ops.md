# Observability, Admin, and Ops

Sector G adds a protected MVP debugging surface for the local demo.

## Admin portal

- Open `http://localhost:3001/admin`.
- Sign in with Clerk.
- Use the dashboard to inspect API status, Celery worker visibility, Redis `media` queue depth, recent jobs, recent videos, and per-video debug details.

The portal calls protected API endpoints through the existing same-origin Next.js backend proxy.

## API endpoints

- `GET /healthz/live` checks API liveness.
- `GET /healthz` checks API dependencies: PostgreSQL, Redis, and MinIO.
- `GET /admin/ops` checks API, Celery worker inspect, and Redis media queue depth.
- `GET /admin/videos` lists recent videos for debugging.
- `GET /admin/jobs` lists recent processing jobs with video failure context.
- `GET /admin/videos/{video_id}/debug` returns video metadata, renditions, processing jobs, and recent playback events.
- `POST /videos/{video_id}/events` records player events for accessible videos.

## Debug flow

1. Check `GET /admin/ops`.
2. If the worker is offline, confirm `docker compose ps worker redis`.
3. If Redis queue depth is increasing, check worker logs:
   ```sh
   docker compose logs -f worker
   ```
4. If a video is `failed`, open `/admin`, select the video, and inspect:
   - `failure_code` / `failure_message` on the video.
   - latest processing job `error_code` / `error_message`.
   - worker log lines with `sector=D` and matching `video_id` / `job_id`.
5. If playback fails, inspect recent playback events and API logs for `sector=G stage=hls_asset_missing`.

User-facing API errors remain sanitized. Developer logs include sector/stage and relevant `video_id` / `job_id` context.
