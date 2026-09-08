# Processing, Publication, and Deletion Runbook

Status: local MVP operations and evidence guide
Scope: Plan 3 media publication/deletion hardening

This runbook describes the current private MinIO, PostgreSQL, Redis, Celery,
FastAPI, and worker contract. It is an operator aid for local and Compose
verification. It is not deployment approval or production qualification.

## Storage and state contract

Generated HLS assets are written only to the immutable attempt prefix:

```text
processed/{video_id}/attempts/{generation}/hls/{relative_path}
```

The worker returns an inventory record for every uploaded file containing its
storage key, HLS-rooted relative path, content type, byte size, and SHA-256.
Failure cleanup deletes only the matching attempt prefix. The legacy
`processed/{video_id}/hls/` prefix is not current worker output and is rejected
by inventory-bound playback.

Publication validates the master, every rendition playlist and segment, and
the generated thumbnail before one fenced psycopg transaction inserts
`video_asset_inventory` and updates job, rendition, thumbnail, and video
publication state. The fence matches video, job, generation, and active
generation, requires a non-tombstoned video, and rolls back all publication
rows if a later condition fails. The prior published attempt is cleaned only
after the transaction commits.

Deletion is tombstone-first. The owner DELETE transaction locks the row, sets
`deleted_at`, `deletion_status=pending`, clears
`active_processing_generation`, fences queued/running processing work, and
returns HTTP 202 before storage I/O. Normal reads and mutations treat that
video as missing. Fresh-session cleanup removes the original and the scoped
`processed/{video_id}/` prefix, then marks the tombstone complete and clears
storage pointers. A failure sets `deletion_status=failed` with a sanitized
error and retains retryable state. Reconciliation never clears `deleted_at` or
restores a processing generation.

## Operator commands

Run from the repository root with the Compose environment available.

### Inspect stale processing jobs

Dry run is the default and performs no state transition:

```sh
make processing-recover-stale
```

Expected output identifies the number of eligible stale running jobs and their
video/job/generation context without enqueuing work. To apply the bounded
failure transition explicitly:

```sh
make processing-recover-stale ARGS="--apply"
```

Apply mode conditionally fails only the captured running job and matching
active generation. A zero-row conditional update means another actor already
changed the state; inspect Compose logs before retrying. This command never
automatically retries or enqueues a replacement job.

### Reconcile deletion tombstones

The Make target is an explicit apply operation for pending, running, and
failed tombstones:

```sh
make deletion-reconcile
```

The command opens fresh sessions, claims each eligible tombstone conditionally,
deletes the original and scoped processed prefix through the private storage
abstraction, and records `complete` only after both cleanup phases succeed.
Missing objects are treated idempotently. Storage or database failures leave a
sanitized `deletion_error`, preserve retryable pointers/state, and log the
video ID and cleanup stage. Re-run the same command after the dependency is
healthy.

To inspect the command interface without applying cleanup:

```sh
cd apps/api
python -m app.commands.reconcile_deletions --help
```

The command requires the configured database/storage environment when it is
run for real. Never put Clerk, MinIO, database, or Redis secret values in shell
history, logs, tickets, or this runbook; use the repository's environment
files/secret injection mechanism.

## Deterministic validation

These checks run without claiming a deployed environment:

```sh
make lint
make test
docker compose run --rm --build api pytest tests/test_video_deletion.py tests/test_storage.py -q
docker compose run --rm --build worker pytest tests/test_packager.py tests/test_repository.py -q
git diff --check
```

The expected result is a zero exit status with the focused and full suites
green. Compile and lint failures are implementation failures, not evidence to
waive. Preserve the exact command and output in the Plan 3 handoff.

## Compose smoke

The smoke harness exercises the local API/web/worker path, private-by-default
behavior, upload through processing, API-owned HLS playback, and failure
handling. Do not stop an unrelated listener. If `127.0.0.1:3001` is occupied,
run the alternate-port smoke:

```sh
WEB_PORT=3002 WEB_SMOKE_URL=http://127.0.0.1:3002 make smoke
```

Record the default-port limitation and the alternate-port result separately.
The smoke result is local Compose evidence only. It does not qualify an
authenticated browser session, a deployed worker, or production storage.

## Failure handling and logs

- Keep the tombstone when cleanup fails; do not manually clear `deleted_at` or
  restore `active_processing_generation`.
- Retry with `make deletion-reconcile` after fixing the dependency. Repeated
  runs are expected to be idempotent when objects are already absent.
- Include `video_id`, `job_id` where available, generation, status, and stage in
  operator diagnostics. User-facing errors must remain sanitized.
- Never delete a broad bucket or prefix. Processed cleanup is scoped to
  `processed/{video_id}/`; attempt cleanup is scoped to one generation.

## Evidence boundaries

1. Local deterministic tests and `compileall` prove repository behavior in the
   test/container environment.
2. Compose smoke proves the local multi-service path and is still local
   evidence.
3. Authenticated/browser qualification requires a separate approved session
   and browser run; it is not implied by this runbook.
4. Merge and deployment require the parent release process and an attributable
   current SHA; neither is performed here.
5. Production readiness requires deployed revision, secret, migration,
   storage, worker, observability, rollback, and authenticated qualification
   evidence; it is not claimed by Plan 3 closeout.
