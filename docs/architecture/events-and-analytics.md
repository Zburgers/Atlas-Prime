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

The watch client records player readiness, play, pause, seek, buffering start/end, ended, HLS quality changes, and fatal playback errors through `POST /videos/{video_id}/events`. Progress pings are emitted no more than once per 15 seconds of media position, so they remain useful raw diagnostic signals without writing an event for every browser time update.

Playback events include the originating recommendation request ID when present. This keeps discovery results joinable to actual viewing behavior. They are not yet used to calculate creator watch-time aggregates; that remains an explicit future aggregation change.

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
