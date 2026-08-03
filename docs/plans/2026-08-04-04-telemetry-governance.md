# Playback Telemetry Governance Implementation Plan

> **For implementation agents:** Use `shipyard:shipyard-executing-plans` and execute task IDs strictly in order.

**Goal:** Keep playback diagnostics useful while bounding anonymous writes, duplicates, raw-data lifetime, and privacy exposure.

**Architecture:** Identify playback sessions and events with client-generated UUIDs, enforce deduplication in PostgreSQL, use Redis fixed-window counters for admission control, and purge raw events with one scheduled retention task. Aggregates remain reproducible from retained source rows.

**Tech Stack:** FastAPI, PostgreSQL/Alembic, Redis, Celery Beat, Next.js/hls.js client, pytest.

---

## Entry Gate And Required Ruling

Plan 3 is COMPLETE. Owner ruling R-004 must be recorded in the handbook before Task 4.1. The ruling must provide:

- raw playback-event retention days;
- whether a one-way HMAC of client IP may be used only for rate limiting;
- per-client/video events-per-minute limit;
- which noisy events may be sampled.

Recommended defaults for approval are 30 days, HMAC allowed with daily salt and never persisted in event rows, 120 events/minute/client/video, and progress pings sampled at the existing 15-second media-position cadence. Agents must not silently adopt these recommendations.

<task id="4.1" name="Add session and event identity">
  <description>Make event retries idempotent and attributable to a bounded playback session.</description>
  <files>
    <create>apps/api/alembic/versions/&lt;timestamp&gt;_telemetry_governance.py</create>
    <modify>apps/api/app/db/models.py</modify>
    <modify>apps/api/app/schemas/videos.py</modify>
    <modify>apps/api/tests/test_analytics_events.py</modify>
  </files>
  <steps>
    <step>Add non-null playback_session_id and event_id UUID values to new events, with unique event_id.</step>
    <step>Keep a migration-compatible nullable/backfill path for historical rows.</step>
    <step>Return the existing row for duplicate event_id instead of inserting again.</step>
    <step>Test same-event retry and same-session distinct events.</step>
  </steps>
  <verification>
    <command>docker compose run --rm --build api pytest tests/test_analytics_events.py -q</command>
    <expected>PASS; duplicate event_id creates one row</expected>
  </verification>
</task>

<task id="4.2" name="Emit stable client telemetry identifiers">
  <description>Generate one playback session per watch load and one event UUID per emitted event.</description>
  <files>
    <modify>apps/web/app/components/video-api.ts</modify>
    <modify>apps/web/app/watch/[videoId]/watch-client.tsx</modify>
    <modify>apps/web/tests/smoke.test.js</modify>
  </files>
  <steps>
    <step>Create playback_session_id once per watch component mount.</step>
    <step>Create event_id once before each network attempt and reuse it for a retry.</step>
    <step>Keep telemetry best-effort and preserve request_id joins.</step>
  </steps>
  <verification>
    <command>docker compose run --rm --build web-test npm --workspace apps/web test</command>
    <expected>PASS; IDs are valid, stable across retry, and request joins remain present</expected>
  </verification>
</task>

<task id="4.3" name="Enforce Redis admission limits">
  <description>Bound anonymous and authenticated event writes using the approved R-004 policy.</description>
  <files>
    <create>apps/api/app/services/telemetry_admission.py</create>
    <modify>apps/api/app/api/videos.py</modify>
    <modify>apps/api/app/core/config.py</modify>
    <modify>.env.example</modify>
    <modify>apps/api/tests/test_analytics_events.py</modify>
  </files>
  <steps>
    <step>Add fixed-window Redis keys derived from approved client identity policy, video id, and minute.</step>
    <step>Set TTL atomically and fail with 429 after the approved limit; never store raw IP in event rows or logs.</step>
    <step>Fail closed for writes when admission storage is unavailable while leaving playback unaffected.</step>
    <step>Test boundary, reset, separate-video, and Redis-failure behavior.</step>
  </steps>
  <verification>
    <command>docker compose run --rm --build api pytest tests/test_analytics_events.py -q</command>
    <expected>PASS; limit is deterministic and playback reads remain unaffected</expected>
  </verification>
</task>

<task id="4.4" name="Add deterministic raw-event retention">
  <description>Purge events older than the approved period through a bounded, observable task.</description>
  <files>
    <create>apps/api/app/services/telemetry_retention.py</create>
    <create>apps/api/app/commands/purge_telemetry.py</create>
    <modify>apps/api/app/worker/analytics.py</modify>
    <modify>Makefile</modify>
    <create>apps/api/tests/test_telemetry_retention.py</create>
  </files>
  <steps>
    <step>Add dry-run command reporting cutoff and row counts.</step>
    <step>Add explicit --apply deletion in bounded batches and schedule one daily Celery task after analytics rebuild.</step>
    <step>Log aggregate counts only; never log client identifiers.</step>
    <step>Test exact cutoff, rerun idempotency, and bounded batches.</step>
  </steps>
  <verification>
    <command>docker compose run --rm --build api pytest tests/test_telemetry_retention.py tests/test_analytics_worker.py -q</command>
    <expected>PASS; rows before cutoff are purged deterministically and rerun is safe</expected>
  </verification>
</task>

<task id="4.5" name="Expose operator telemetry health">
  <description>Make accepted, duplicate, rate-limited, and purged counts visible without exposing client data.</description>
  <files>
    <modify>apps/api/app/api/admin.py</modify>
    <modify>apps/api/app/schemas/videos.py</modify>
    <modify>apps/web/app/admin/admin-dashboard.tsx</modify>
    <modify>apps/api/tests/test_recommendation_logging.py</modify>
  </files>
  <steps>
    <step>Add aggregate-only protected operations metrics.</step>
    <step>Render counts and retention cutoff in Admin; no IP hash, session ID, or event ID list.</step>
    <step>Test admin/non-admin access.</step>
  </steps>
  <verification>
    <command>docker compose run --rm --build api pytest tests/test_recommendation_logging.py -q</command>
    <expected>PASS; only allowlisted admin sees aggregate telemetry health</expected>
  </verification>
</task>

<task id="4.6" name="Close telemetry phase">
  <description>Document approved policy, validation, and one handoff.</description>
  <files>
    <modify>docs/architecture/events-and-analytics.md</modify>
    <modify>docs/PRODUCT_SPEC_AND_ENGINEERING_HANDBOOK.md</modify>
    <modify>docs/plans/README.md</modify>
    <create>memory/DDMMYY-BEG-telemetry-governance.md</create>
  </files>
  <steps>
    <step>Record R-004 decision and operational commands.</step>
    <step>Create exactly one memory entry for this agent handoff.</step>
    <step>Run exit gate and record exact evidence SHA.</step>
  </steps>
  <verification>
    <command>make lint &amp;&amp; make test &amp;&amp; make smoke &amp;&amp; git diff --check</command>
    <expected>PASS; Plan 4 COMPLETE and Plan 5 READY</expected>
  </verification>
</task>

## Stop Conditions

- Missing R-004 is a hard blocker, not permission for an agent-selected policy.
- Do not persist raw IP addresses or make telemetry required for playback.
- Any aggregate-definition change must preserve deterministic rebuild tests or be separately approved.
