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

Watch time is currently the sum of `video_views.position_seconds` for counted views. It is a credited watch-time metric, not a reconstruction of every player progress interval. Rich progress events remain a later increment.

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
