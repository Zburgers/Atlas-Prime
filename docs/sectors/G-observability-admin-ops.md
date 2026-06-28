# Sector G — Observability, Admin, and Operations

Owner: observability/ops agent  
Primary mission: make the platform debuggable while it is being built.

## Scope

Build visibility for:

- API health.
- Celery worker health.
- Redis queue/job status.
- Video processing failures.
- Upload/storage failures.
- MinIO storage reachability when relevant.
- Playback errors/events if implemented.
- Basic admin/debug dashboard or endpoints.
- Structured logs where feasible.

## Out of scope

- Enterprise observability stack.
- Multi-region operations.
- On-call system.
- Cost analytics.
- Complex data warehouse.

## Interfaces consumed

From Sector B:

- Video/job schema.
- Status fields.
- Failure fields.

From Sector C:

- Upload/storage errors.

From Sector D:

- Worker logs, durations, failure codes.

From Sector E:

- Playback events/errors.

From Sector H:

- Healthcheck and smoke command conventions.

## Deliverables

- Health endpoints.
- Admin/debug job list endpoint or page.
- Structured log conventions.
- Processing failure visibility.
- Basic metrics counters/timings if feasible.
- Operational runbook notes.

## Acceptance criteria

- [ ] API health is visible.
- [ ] Worker health or last-seen signal is visible.
- [ ] Processing jobs can be listed with status and failure reason.
- [ ] A failed transcode can be debugged from DB/logs without guessing.
- [ ] Upload failures are distinguishable from processing failures.
- [ ] User-facing error messages are sanitized.
- [ ] Developer-facing logs include enough context: video_id, job_id, sector/stage.
- [ ] Admin/debug endpoints are protected if auth exists.

## Suggested implementation order

1. Define log context fields.
2. Add API health endpoint.
3. Add Celery worker heartbeat or job visibility.
4. Add admin job/video debug endpoint.
5. Add player event ingestion if E exposes it.
6. Add runbook notes.

## Latest docs to check

- Logging library docs for the chosen FastAPI/Celery stack.
- Metrics/healthcheck docs for FastAPI.
- Celery monitoring docs if queue visibility or retries are touched.

## Required memory entry

Before handoff, write:

```txt
memory/DDMMYY-G-short-topic.md
```

Use `memory/_TEMPLATE.md`. Include changed interfaces, validation, and handoff risks.

## Required grounding

Before implementation, read:

- `docs/00-ground-truth-mvp-spec.md`
- `docs/01-agent-operating-contract.md`
- This sector manifest
- Recent `memory/` entries for this sector and direct dependencies
- Latest official docs for any framework/tool/API touched
