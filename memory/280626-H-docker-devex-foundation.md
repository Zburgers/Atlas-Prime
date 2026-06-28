# 280626-H-docker-devex-foundation

Sector: H testing, DevEx, and CI
Agent: Codex
Date: 28-06-2026
Branch/Commit: main / commited - 50710216cf1ff69bf1ce7fa377d873b973fd8e90 

## What changed
- Added minimal runnable monorepo scaffold for Next.js web, FastAPI API, Celery media worker, PostgreSQL, Redis, and MinIO.
- Added Compose, `.env.example`, Makefile commands, CI workflow, smoke script, and synthetic media fixture strategy.
- Exposed web on host port `3001`, PostgreSQL on `15432`, and Redis on `16379` to avoid common local service conflicts while keeping container URLs stable.

## Decisions / ADR notes
- Decision: Use Compose healthchecks plus a one-shot MinIO bootstrap service to create private originals and processed buckets.
- Reason: Sector H needs repeatable local startup without making MinIO objects public or requiring manual console steps.
- Alternatives considered: Manual bucket creation, which is easier to forget and weaker for CI.

## Validation
- `docker compose config -q`
- `make test` (API pytest: 3 passed; web node test: 1 passed)
- `make lint` (Compose config, Python compileall, ESLint)
- `make smoke` (web, API, PostgreSQL, Redis, MinIO, and worker all healthy)
- `make fixture` generated ignored synthetic `fixtures/media/sample-2s.mp4`

## Files touched
- compose.yaml
- .env.example
- Makefile
- apps/api/
- apps/web/
- workers/media/
- scripts/
- fixtures/media/README.md
- docs/local-dev.md
- .github/workflows/ci.yml

## Handoff / risks
- Full upload -> process -> playback smoke is contract-only until Sectors C, D, E, and F add upload endpoints, media processing, playback proxy, and auth fixtures.
- Cross-user private playback denial is explicitly pending Sector F auth fixtures.
- `npm audit --omit=dev` reports a moderate PostCSS advisory through current stable `next@16.2.9`; npm's forced fix would downgrade Next and was not applied.
