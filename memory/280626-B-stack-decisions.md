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