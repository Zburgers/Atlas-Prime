# 240826-BEG-telemetry-admission

Sector: B/E/G
Agent: Luna
Date: 24-08-2026
Branch/Commit: docs/fullplatform-rollout / 47e54ff base; Plan 4.3 uncommitted

## What changed
- Added Redis-backed fixed-window admission for new playback-event writes, capped at 120 events per UTC minute per video and client scope.
- Authenticated scopes use `user:{database_uuid}`; anonymous scopes use `session:{playback_session_id}`. No IP or derived-IP value is used, persisted, or logged.
- Admission runs after access and same-video duplicate checks, before DB insertion; 429 is returned at the limit and Redis failures return sanitized 503 without affecting playback reads.

## Decisions / ADR notes
- Decision: use the existing `CELERY_BROKER_URL` with its `REDIS_URL` fallback, key namespace `atlas:telemetry:admission:v1`, UTC `YYYYMMDDHHMM` buckets, and a 125-second TTL.
- Reason: the transactional `redis.asyncio` pipeline performs `INCR` and `EXPIRE` atomically while safely covering the one-minute bucket boundary without adding another secret-bearing configuration value.
- Alternatives considered: raw-IP/derived-IP scopes, durable DB counters, and an independently configured Redis URL were rejected by the owner policy or unnecessary for this write-path control.

## Validation
- `docker compose run --rm --build api pytest tests/test_analytics_events.py -q` -> PASS, 10 passed in 3.59s.
- `docker compose run --rm --build api pytest tests/test_analytics_events.py tests/test_video_api.py tests/test_recommendation_logging.py -q` -> PASS, 55 passed in 10.06s.
- `docker compose run --rm --build api python -m compileall -q app/services/telemetry_admission.py app/api/videos.py tests/test_analytics_events.py` -> PASS.
- `ruff check apps/api/app/services/telemetry_admission.py apps/api/app/api/videos.py apps/api/tests/test_analytics_events.py` -> PASS; API image did not include Ruff, so host Ruff was used.
- `git diff --check` -> PASS.
- No full-stack smoke, Plan 4 completion, commit, or push was performed.

## Files touched
- `apps/api/app/services/telemetry_admission.py`
- `apps/api/app/api/videos.py`
- `apps/api/tests/test_analytics_events.py`
- `memory/240826-BEG-telemetry-admission.md`

## Handoff / risks
- Duplicate event IDs return before admission and therefore do not consume a slot; cross-video conflicts also remain fenced before admission.
- A DB failure after a successful Redis admission can consume a slot without creating a row; the bounded operational counter expires with its window and playback remains unaffected.
- Redis admission state is ephemeral only. Retention, aggregate telemetry health, full-stack qualification, and Plan 4 completion remain later tasks.
