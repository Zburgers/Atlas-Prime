# Events And Analytics

## Scope

Atlas Prime keeps raw impression and counted-view events as the source of truth. Daily aggregates are derived data for Creator Studio and operations views.

## Data Flow

```txt
browser event -> API validation/access check -> raw event table
operator rebuild -> video_daily_metrics + creator_daily_metrics
Studio analytics -> creator-owned aggregate rows
```

`video_daily_metrics` and `creator_daily_metrics` contain UTC calendar-day totals for impressions, counted views, and watch time.

Watch time is currently the sum of `video_views.position_seconds` for counted views. It is a credited watch-time metric, not a reconstruction of every player progress interval.

## Playback telemetry

Raw playback telemetry is retained for 30 days. Admission is capped at 120 events per UTC minute per client/video. No IP address or derived IP identifier is persisted; Redis admission and health counters are ephemeral operational state only and are not exposed as event data.

The watch client records player readiness, play, pause, seek, buffering start/end, ended, HLS quality changes, and fatal playback errors through `POST /videos/{video_id}/events`. Progress pings are emitted no more than once per 15 seconds of media position, so they remain useful raw diagnostic signals without writing an event for every browser time update.

Playback events include the originating recommendation request ID when present. This keeps discovery results joinable to actual viewing behavior. They are not yet used to calculate creator watch-time aggregates; that remains an explicit future aggregation change.

### Playback event identity and deduplication

New events carry non-null UUID `playback_session_id` and `event_id` values. Migration `20260824_0019_telemetry_governance` deterministically backfilled historical rows before enforcing the final non-null columns and unique `event_id` constraint. A same-video retry for an existing `event_id` returns the existing event with HTTP 200 and does not repeat side effects such as play-history recording. Reuse of an event ID for another video is rejected after access to the requested video is checked.

The watch and feed producers create one session identity per watch/card load and one event identity per logical event. A bounded transient retry reuses the same event ID; telemetry remains best-effort and never blocks playback or navigation.

### Admission and privacy boundary

New writes are admitted after readable-video access and same-video duplicate checks. Authenticated clients use `user:{database_user_uuid}` scope; anonymous clients use `session:{playback_session_id}` scope. The fixed-window Redis key contains the admission namespace, client scope, video UUID, and UTC minute bucket, with an atomic increment/TTL operation. No IP, IP hash, device fingerprint, session identity, or event identity is copied into raw event data or logs.

Admission state is separate from the aggregate health namespace. The protected aggregate endpoint reads only `atlas:telemetry:metrics:v1:accepted`, `duplicate`, `rate_limited`, and `purged` counters, plus the current retention cutoff and status. It never returns event rows or client/video/session identifiers. Missing counters are zero; Redis read failure returns a sanitized degraded response without removing access to the other admin panels. Metric writes are best-effort and cannot change event or playback correctness.

### Retention and operations

Raw rows are eligible only when `created_at < now_utc - 30 days`; a row exactly at the cutoff is retained. `make telemetry-purge` is dry-run by default and reports aggregate cutoff/count data. Deletion requires `make telemetry-purge ARGS="--apply"` and runs in bounded batches. The existing analytics worker/beat schedules one purge at 00:20 UTC after the daily rebuild at 00:05 UTC. Manual and scheduled purges update only the aggregate `purged` health counter after successful deletion summaries. Logs and command output contain aggregate status, cutoff, batch, and count data only.

### Closeout evidence boundary

At parent-verified implementation SHA `3021889`, the local gates passed `make lint`, `make test` (145 API, 25 worker, 9 web), `WEB_PORT=3003 WEB_SMOKE_URL=http://127.0.0.1:3003 make smoke`, and `git diff --check`. Local/browser qualification also covered the public web routes, 390px overflow, keyboard focus names, and Lighthouse accessibility 100 with zero failing audits on the rebuilt artifact. These are local/browser artifacts only, not CI, merge, deployment, authenticated admin-role, or production qualification; Lighthouse results are not a WCAG certification.

## Rebuild Contract

The rebuild deletes aggregate rows for the supplied inclusive UTC date range, then recreates them from raw `video_impressions` and `video_views`. It is deterministic and safe to rerun for the same source data.

```bash
make analytics-rebuild DATE_FROM=2026-07-01 DATE_TO=2026-07-12
```

The equivalent protected operations endpoint is:

```txt
POST /admin/analytics/rebuild?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD
```

Only Clerk user IDs listed in `ATLAS_ADMIN_CLERK_USER_IDS` can invoke the endpoint. Creator-facing data is available through `GET /studio/analytics?days=28` and is always scoped to the signed-in owner.

## Scheduled aggregation

`analytics-worker` consumes only the dedicated `analytics` Celery queue. `analytics-beat` is the single scheduler and enqueues `analytics_worker.rebuild_daily_metrics` at 00:05 UTC each day. The task rebuilds the current and previous UTC dates so delayed event writes can be incorporated safely. It reuses the same deterministic rebuild service as the protected admin endpoint and `make analytics-rebuild` command.

Do not run more than one beat scheduler for this task; Celery Beat schedulers are publishers, not distributed locks. The media worker continues to consume only `media` jobs and must not be used for analytics aggregation.
