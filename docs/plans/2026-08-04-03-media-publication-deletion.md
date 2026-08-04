# Media Publication And Deletion Implementation Plan

> **For implementation agents:** Use `shipyard:shipyard-executing-plans` and execute task IDs strictly in order.

**Goal:** Publish immutable HLS generations atomically, prevent stale worker writes, bind served segments to published output, and make deletion truthful and recoverable.

**Architecture:** Workers upload to `processed/{video_id}/attempts/{generation}/hls/`; the database publishes one generation only after all expected assets exist. Deletion writes a durable tombstone before cleanup, and every worker mutation checks that tombstone and active generation.

**Tech Stack:** MinIO/S3, PostgreSQL, Alembic, FastAPI, Psycopg, Celery, FFmpeg HLS, pytest.

---

## Entry Gate

Plan 2 is COMPLETE with an evidence SHA and the generation value is present in video state, job rows, Celery payloads, and worker conditional updates. Read Sectors B, C, D, E, G, and H. Do not parallelize storage layout, deletion, or serving tasks.

<task id="3.1" name="Persist publication and deletion state">
  <description>Add the durable fields and segment inventory needed by C-006 through C-009.</description>
  <files>
    <create>apps/api/alembic/versions/&lt;timestamp&gt;_media_publication_deletion.py</create>
    <modify>apps/api/app/db/models.py</modify>
    <modify>apps/api/app/domain/status.py</modify>
    <create>apps/api/tests/test_media_publication_schema.py</create>
  </files>
  <steps>
    <step>Add videos.deleted_at, deletion_status with pending|running|failed|complete, and deletion_error fields without adding a video lifecycle status.</step>
    <step>Add video_asset_inventory keyed by video id, generation, relative path, content type, size, and immutable checksum.</step>
    <step>Index active generation/path uniquely and make migration/downgrade complete.</step>
    <step>Test clean upgrade and constraints.</step>
  </steps>
  <verification>
    <command>docker compose run --rm --build api alembic upgrade head &amp;&amp; docker compose run --rm --build api pytest tests/test_media_publication_schema.py -q</command>
    <expected>One Alembic head and passing schema tests</expected>
  </verification>
</task>

<task id="3.2" name="Upload attempt-scoped immutable assets">
  <description>Stop overwriting the current deterministic HLS tree before success.</description>
  <files>
    <modify>workers/media/media_worker/packager.py</modify>
    <modify>workers/media/media_worker/storage.py</modify>
    <modify>workers/media/media_worker/celery_app.py</modify>
    <modify>workers/media/tests/test_packager.py</modify>
  </files>
  <steps>
    <step>Generate storage keys beneath attempts/{generation}/hls while preserving relative playlist layout.</step>
    <step>Return uploaded key, relative path, size, content type, and SHA-256 inventory.</step>
    <step>On upload failure, delete only that attempt prefix; never delete the currently published generation.</step>
    <step>Add failure-on-Nth-upload and idempotent cleanup tests.</step>
  </steps>
  <verification>
    <command>docker compose run --rm --build worker pytest tests/test_packager.py -q</command>
    <expected>PASS; partial attempt is removed and published generation is untouched</expected>
  </verification>
</task>

<task id="3.3" name="Atomically publish inventory and generation">
  <description>Expose a generation only when its complete manifest, playlists, segments, and thumbnail are committed together.</description>
  <files>
    <modify>workers/media/media_worker/repository.py</modify>
    <modify>workers/media/media_worker/celery_app.py</modify>
    <modify>workers/media/tests/test_repository.py</modify>
  </files>
  <steps>
    <step>Add tests for complete publish, missing master, empty rendition, stale generation, and deleted video.</step>
    <step>Insert inventory and update manifest/thumbnail/renditions/video/job in one transaction guarded by active generation and deleted_at is null.</step>
    <step>Reject stale/deleted finalization and cleanup its attempt prefix.</step>
    <step>Keep old published generation until the new transaction succeeds; cleanup old generation only afterward.</step>
  </steps>
  <verification>
    <command>docker compose run --rm --build worker pytest tests/test_repository.py -q</command>
    <expected>PASS; no incomplete or stale generation becomes visible</expected>
  </verification>
</task>

<task id="3.4" name="Serve only published inventory assets">
  <description>Close C-009 for proxy and signed-redirect delivery.</description>
  <files>
    <modify>apps/api/app/api/videos.py</modify>
    <modify>apps/api/app/services/videos.py</modify>
    <modify>apps/api/tests/test_playback_delivery.py</modify>
    <modify>scripts/smoke-devex.sh</modify>
  </files>
  <steps>
    <step>Add red tests for a correctly patterned but uninventoried segment and a segment from an old generation.</step>
    <step>Resolve every playlist, segment, and thumbnail through the active published inventory after existing traversal/access checks.</step>
    <step>Keep signed playlist rewriting relative order unchanged and redirect only inventoried segment keys.</step>
    <step>Extend smoke to request one rejected uninventoried path.</step>
  </steps>
  <verification>
    <command>docker compose run --rm --build api pytest tests/test_playback_delivery.py -q</command>
    <expected>PASS; uninventoried and stale-generation assets return 404</expected>
  </verification>
</task>

<task id="3.5" name="Tombstone before video deletion cleanup">
  <description>Close C-007 and C-008 without falsely returning terminal deletion while storage cleanup can fail.</description>
  <files>
    <modify>apps/api/app/services/videos.py</modify>
    <modify>apps/api/app/api/videos.py</modify>
    <modify>apps/api/app/services/storage.py</modify>
    <create>apps/api/app/commands/reconcile_deletions.py</create>
    <modify>Makefile</modify>
    <create>apps/api/tests/test_video_deletion.py</create>
  </files>
  <steps>
    <step>Write race tests for delete while queued, running, uploading, and immediately before worker finalize.</step>
    <step>Commit deleted_at/deletion_status pending and clear active generation before object cleanup starts.</step>
    <step>Make all normal reads/mutations treat tombstoned videos as missing; worker guards from Plan 2 must reject them.</step>
    <step>After the tombstone is committed return 202 with an API-owned deletion status; enqueue cleanup, retain a failed tombstone on errors, and never report terminal success before all required cleanup is complete.</step>
    <step>Add an admin-only, idempotent reconciliation command for failed tombstones; do not resurrect content.</step>
  </steps>
  <verification>
    <command>docker compose run --rm --build api pytest tests/test_video_deletion.py -q</command>
    <expected>PASS; deleted media is unreadable immediately, deletion status is observable, and cleanup failures remain retryable without resurrection</expected>
  </verification>
</task>

<task id="3.6" name="Close media publication and deletion phase">
  <description>Update cross-sector contracts and record whole-stack evidence.</description>
  <files>
    <modify>docs/api-database.md</modify>
    <modify>docs/delivery-playback-cdn.md</modify>
    <modify>docs/PRODUCT_SPEC_AND_ENGINEERING_HANDBOOK.md</modify>
    <modify>docs/plans/README.md</modify>
    <create>docs/runbooks/processing-publication-deletion.md</create>
    <create>memory/DDMMYY-BCDEG-media-publication-deletion.md</create>
  </files>
  <steps>
    <step>Document generation layout, inventory, tombstone semantics, reconciliation, and rollback.</step>
    <step>Create exactly one memory entry for this agent handoff.</step>
    <step>Run exit gate on a clean stack and record exact evidence SHA.</step>
  </steps>
  <verification>
    <command>make lint &amp;&amp; make test &amp;&amp; make smoke &amp;&amp; git diff --check</command>
    <expected>PASS; Plan 3 COMPLETE and Plan 4 eligible after R-004</expected>
  </verification>
</task>

## Stop Conditions

- Do not mutate the legacy published prefix in place or make processed buckets public.
- A different deletion completion model, lifecycle status addition, or object-layout change requires an ADR-level owner ruling.
- Any private/unlisted playback or signed-delivery regression blocks promotion.
