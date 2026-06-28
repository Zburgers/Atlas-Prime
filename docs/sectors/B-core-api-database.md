# Sector B — Core API and Database

Owner: backend/domain agent  
Primary mission: define the durable domain model, API contracts, and state machine.

## Scope

Build the backend foundation:

- FastAPI route/service foundation.
- Database schema/migrations with SQLAlchemy ORM and Alembic.
- Video domain model.
- Video lifecycle/status machine.
- API endpoints for video metadata and processing status.
- Job record model.
- Clean service boundaries for upload, processing, playback, and auth sectors.

## Out of scope

- Actual video transcoding.
- Browser player UI.
- CDN integration.
- Live streaming.
- Recommendations.

## Interfaces provided

To Sector A:

- Video list/detail response.
- Create/update video metadata.
- Processing status response.

To Sector C:

- Video row creation/update.
- Original storage key field.
- Upload completion transition.

To Sector D:

- Processing job model.
- Job claim/update APIs or worker DB access patterns.
- Rendition model.

To Sector E:

- Playback metadata endpoint.
- HLS master storage key.

To Sector G:

- Admin/debug queries for videos/jobs.

## Required domain statuses

Use the canonical statuses from the main spec:

```txt
draft, uploading, uploaded, queued, probing, processing, ready, failed
```

If the implementation uses enums, these exact string values are preferred for clarity.

## Deliverables

- Initial schema/migrations for users, videos, renditions, processing jobs, and optionally playback events.
- FastAPI route skeletons for core video operations.
- Status transition helpers or service functions.
- Error model for user-safe and developer-facing errors.
- API response examples or FastAPI OpenAPI output.
- Basic tests for status transitions and ownership-aware queries.

## Acceptance criteria

- [ ] Migrations run from a clean database.
- [ ] Database access pattern is documented clearly enough for other sectors to avoid guessing session/transaction boundaries.
- [ ] Video can be created in `draft` or equivalent initial state.
- [ ] Video status can transition through the canonical lifecycle.
- [ ] Invalid status transitions are rejected or explicitly handled.
- [ ] Video ownership is represented in the schema.
- [ ] Processing jobs are durable and queryable.
- [ ] Renditions can be stored per video.
- [ ] API returns stable, documented response shapes.
- [ ] Dependent sectors can integrate without guessing DB internals.

## Suggested implementation order

1. Define schema and migrations.
2. Define status enum/state helpers.
3. Add video CRUD endpoints.
4. Add processing job endpoints/service functions.
5. Add rendition model and playback metadata shape.
6. Add tests.
7. Document endpoint examples.

## Latest docs to check

- FastAPI docs for routing, validation, dependency injection, and file-safe error handling.
- SQLAlchemy ORM docs.
- Alembic docs.
- PostgreSQL docs if using advanced enum/check constraints.


## Required memory entry

Before handoff, write:

```txt
memory/DDMMYY-B-short-topic.md
```

Use `memory/_TEMPLATE.md`. Include changed interfaces, validation, and handoff risks.

## Required grounding

Before implementation, read:

- `docs/00-ground-truth-mvp-spec.md`
- `docs/01-agent-operating-contract.md`
- This sector manifest
- Recent `memory/` entries for this sector and direct dependencies
- Latest official docs for any framework/tool/API touched
