# Upload And Job Idempotency Implementation Plan

> **For implementation agents:** Use `shipyard:shipyard-executing-plans` and execute task IDs strictly in order.

**Goal:** Ensure one authoritative upload/processing generation survives concurrent requests, Celery redelivery, and stale worker completion.

**Architecture:** Store an immutable generation identifier on each processing job and the active generation on the video. Claim uploads and jobs with database compare-and-set operations; every worker stage/finalization update must match the active generation.

**Tech Stack:** PostgreSQL, Alembic, SQLAlchemy async ORM, Psycopg worker repository, Celery, pytest.

---

## Entry Gate

Plan 1 is COMPLETE in `docs/plans/README.md`, its exact evidence SHA is present, and `make test` is green at that SHA. Read Sectors B, C, D, F, and H. Tasks are sequential because all share lifecycle and schema contracts.

<task id="2.1" name="Add processing generation schema">
  <description>Create one generation identity shared by video, upload, job payload, and worker transitions.</description>
  <files>
    <create>apps/api/alembic/versions/&lt;timestamp&gt;_processing_generations.py</create>
    <modify>apps/api/app/db/models.py</modify>
    <modify>apps/api/tests/test_video_status.py</modify>
  </files>
  <steps>
    <step>Add nullable videos.active_processing_generation and non-null video_processing_jobs.generation UUID fields.</step>
    <step>Add a PostgreSQL partial unique index allowing at most one queued/running job per video.</step>
    <step>Backfill existing jobs deterministically during migration; keep downgrade complete.</step>
    <step>Test ORM constraints and clean upgrade to head.</step>
  </steps>
  <verification>
    <command>docker compose run --rm --build api alembic upgrade head &amp;&amp; docker compose run --rm --build api pytest tests/test_video_status.py -q</command>
    <expected>Migration reaches one head and schema tests PASS</expected>
  </verification>
</task>

<task id="2.2" name="Atomically claim original upload">
  <description>Close C-004 by allowing exactly one request to transition draft/failed to uploading.</description>
  <files>
    <modify>apps/api/app/services/uploads.py</modify>
    <modify>apps/api/tests/test_video_api.py</modify>
  </files>
  <steps>
    <step>Add an async concurrency test issuing two upload requests for the same video.</step>
    <step>Replace read-then-write claim with one conditional UPDATE returning the claimed video/generation.</step>
    <step>Remove uploading from accepted starting states; loser returns 409 without storage or queue side effects.</step>
    <step>Ensure queue failure marks only the matching generation failed.</step>
  </steps>
  <verification>
    <command>docker compose run --rm --build api pytest tests/test_video_api.py -q</command>
    <expected>PASS; exactly one upload request owns side effects</expected>
  </verification>
</task>

<task id="2.3" name="Carry generation through queue payload">
  <description>Bind every processing task to the job generation created by the upload transaction.</description>
  <files>
    <modify>apps/api/app/services/processing_queue.py</modify>
    <modify>apps/api/app/services/uploads.py</modify>
    <modify>apps/api/tests/test_video_api.py</modify>
  </files>
  <steps>
    <step>Add generation to enqueue_video_processing and media_worker.process_video arguments.</step>
    <step>Assert queued job, videos.active_processing_generation, and Celery payload match.</step>
    <step>Keep public upload response redacted per Plan 1.</step>
  </steps>
  <verification>
    <command>docker compose run --rm --build api pytest tests/test_video_api.py -q</command>
    <expected>PASS; persisted and queued generation values are identical</expected>
  </verification>
</task>

<task id="2.4" name="Fence worker stage and terminal updates">
  <description>Close the remaining C-005 gap so stale or redelivered tasks cannot mutate a newer generation.</description>
  <files>
    <modify>workers/media/media_worker/celery_app.py</modify>
    <modify>workers/media/media_worker/repository.py</modify>
    <modify>workers/media/tests/test_repository.py</modify>
  </files>
  <steps>
    <step>Add repository tests for duplicate claim, stale stage update, stale success, and stale failure.</step>
    <step>Require job id, generation, running status, and videos.active_processing_generation in every conditional update.</step>
    <step>Make terminal methods return an applied boolean; a stale terminal update logs and exits without changing video state.</step>
    <step>Keep Celery late acknowledgements and bounded one-job claim behavior.</step>
  </steps>
  <verification>
    <command>docker compose run --rm --build worker pytest tests/test_repository.py -q</command>
    <expected>PASS; stale/redelivered task cannot finalize or fail a newer generation</expected>
  </verification>
</task>

<task id="2.5" name="Add bounded stale-job recovery">
  <description>Provide one explicit operator recovery path for genuinely abandoned running jobs.</description>
  <files>
    <modify>apps/api/app/core/config.py</modify>
    <create>apps/api/app/commands/recover_stale_jobs.py</create>
    <modify>apps/api/app/services/processing_queue.py</modify>
    <modify>Makefile</modify>
    <modify>.env.example</modify>
    <create>apps/api/tests/test_processing_recovery.py</create>
  </files>
  <steps>
    <step>Pin ATLAS_PROCESSING_STALE_SECONDS default to 900 with a validated lower bound of 60.</step>
    <step>Add a dry-run-by-default command that identifies running jobs older than the threshold.</step>
    <step>Require explicit --apply; conditionally fail the matching generation and never enqueue unbounded retries.</step>
    <step>Add make processing-recover-stale ARGS='--apply' and tests for fresh, stale, and superseded jobs.</step>
  </steps>
  <verification>
    <command>docker compose run --rm --build api pytest tests/test_processing_recovery.py -q</command>
    <expected>PASS; recovery is bounded, explicit, and generation-safe</expected>
  </verification>
</task>

<task id="2.6" name="Close idempotency phase">
  <description>Document the generation/job payload interface and promote only after whole-stack evidence.</description>
  <files>
    <modify>docs/api-database.md</modify>
    <modify>docs/PRODUCT_SPEC_AND_ENGINEERING_HANDBOOK.md</modify>
    <modify>docs/plans/README.md</modify>
    <create>memory/DDMMYY-BCD-upload-job-generation.md</create>
  </files>
  <steps>
    <step>Document schema, queue payload, stale recovery command, and rollback risks.</step>
    <step>Create exactly one memory entry for this agent handoff.</step>
    <step>Run exit gate and record exact evidence SHA.</step>
  </steps>
  <verification>
    <command>make lint &amp;&amp; make test &amp;&amp; make smoke &amp;&amp; git diff --check</command>
    <expected>PASS; Plan 2 COMPLETE and Plan 3 READY at one SHA</expected>
  </verification>
</task>

## Stop Conditions

- More than one Alembic head, an inability to express active-job uniqueness, or any lifecycle status addition requires plan revision and owner approval.
- Do not add automatic retries in this plan; recovery is explicit and bounded.
- Do not start attempt-scoped storage changes before the generation contract is merged.
