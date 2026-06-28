# 280626-B-stack-decisions

Sector: B
Agent: Hermes Agent
Date: 28-06-2026
Branch/Commit: 910d6f4 (AGENTS.md commit)

## What changed
- Documented confirmed stack choices for MVP implementation

## Decisions / ADR notes
- Decision: Backend = FastAPI with SQLAlchemy ORM + Alembic migrations
- Reason: Modern async Python framework, clean HTTP contracts, good for media orchestration; SQLAlchemy provides stable ORM, Alembic handles schema evolution
- Alternatives considered: Express/NestJS (rejected - user prefers Python)

- Decision: Auth = Clerk (external provider)
- Reason: Outsourced authentication reduces auth surface area, clean ownership model, integrates with FastAPI via JWT
- Alternatives considered: Custom email/password (deferred - Clerk simplifies MVP)

- Decision: Storage = MinIO from day one (S3-compatible)
- Reason: Future-proof path, same API for local and production, enables direct upload patterns, works with Celery workers
- Alternatives considered: Local filesystem only (rejected - user wants MinIO early for better learning path)

- Decision: Background tasks = Redis + Celery
- Reason: Standard queue pattern, integrates cleanly with FastAPI, persists jobs across restarts
- Alternatives considered: BullMQ (rejected - Python ecosystem prefers Celery)

- Decision: Realtime = defer decision (not needed for VOD MVP)
- Reason: Core upload->process->playback loop is asynchronous; no live streaming or chat required for MVP
- Alternatives considered: WebSockets, long-polling, SSE (all deferred)

## Validation
- Decision aligns with docs/00-ground-truth-mvp-spec.md architecture assumptions (lines 69-82)
- Stack supports all 8 sector requirements

## Files touched
- memory/280626-B-stack-decisions.md (this file)

## Handoff / risks
- **Database connection string**: Must use `postgresql+asyncpg://` for async SQLAlchemy
- **MinIO endpoint**: Will need `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY` env vars
- **Clerk integration**: Will need `CLERK_SECRET_KEY` and frontend publishes `CLERK_PUBLISHABLE_KEY`
- **Redis URL**: Standard `redis://localhost:6379/0` works for local Docker Compose
- **Sector C**: Storage service should be S3/MinIO compatible from the start
- **Sector D**: Worker needs MinIO SDK for reading originals, writing HLS output
- **Sector E**: Playback URLs will be MinIO presigned URLs or served through API
- **Sector H**: Docker Compose must include postgres:15, redis:7, minio/minio

-----

# 280626-H-sector-doc-stack-alignment

Sector: H
Agent: Codex
Date: 28-06-2026
Branch/Commit: Not recorded

## What changed
- Updated sector manifests A-H to reflect the confirmed MVP stack already recorded in `AGENTS.md` and `memory/280626-B-stack-decisions.md`.
- Kept existing scope, plans, and acceptance structure intact while replacing generic stack language with specific contracts for Next.js, FastAPI, SQLAlchemy, Alembic, Clerk, Redis + Celery, and MinIO.

## Decisions / ADR notes
- Decision: Treat the stack choices in `AGENTS.md` and `memory/280626-B-stack-decisions.md` as binding sector-level contracts.
- Reason: Future sector agents need concrete implementation guidance and should not reopen already-set MVP stack choices.
- Alternatives considered: Leaving sector manifests generic, which would keep avoidable ambiguity across sectors.

## Validation
- Reviewed `docs/00-ground-truth-mvp-spec.md`, `docs/01-agent-operating-contract.md`, `memory/README.md`, `memory/_TEMPLATE.md`, and `memory/280626-B-stack-decisions.md` before editing.
- Ran `git diff -- docs/sectors` and targeted `rg` checks to confirm the sector manifests now reference the agreed stack consistently.

## Files touched
- docs/sectors/A-product-web-app-shell.md
- docs/sectors/B-core-api-database.md
- docs/sectors/C-upload-ingest-storage.md
- docs/sectors/D-media-processing-packaging.md
- docs/sectors/E-delivery-playback-cdn.md
- docs/sectors/F-auth-access-control.md
- docs/sectors/G-observability-admin-ops.md
- docs/sectors/H-testing-devex-ci.md
- memory/280626-H-sector-doc-stack-alignment.md

## Handoff / risks
- The sector manifests now assume MinIO from day one, so the main MVP spec still contains a higher-level local-first storage phrasing that should not override sector execution.
- Remaining owner-level decisions still not locked by these edits: ready-video default privacy, upload transport pattern, and final playback URL strategy.
