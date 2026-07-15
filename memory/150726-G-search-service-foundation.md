# 150726-G-search-service-foundation

Sector: G - Observability, Admin, and Platform Operations
Agent: Codex
Date: 15-07-2026
Branch/Commit: docs/fullplatform-rollout

## What changed
- Added a pinned Meilisearch `v1.37` Compose service with persistent storage, a healthcheck, and explicit configuration.
- Made the API health contract report the dedicated search dependency when `ATLAS_SEARCH_BACKEND=meilisearch`.

## Decisions / ADR notes
- Decision: Add Meilisearch as the Phase 5 S1 dedicated search service while preserving PostgreSQL search reads until asynchronous indexing is delivered.
- Reason: The rollout contract requires a health-gated dedicated service before public reads can safely depend on an index.

## Validation
- `docker compose config -q`
- `docker compose up -d search api --build`
- Confirmed `GET /health` returns `{"status":"available"}` and API `/healthz` reports `dependencies.search.ok=true`.

## Files touched
- compose.yaml
- .env.example
- apps/api/app/core/config.py
- apps/api/app/main.py
- docs/local-dev.md

## Handoff / risks
- Local development uses the Meilisearch development environment without a master key; production must set a 16+-character `MEILISEARCH_MASTER_KEY` and `MEILI_ENV=production`.
- No documents are indexed yet. The next slice must add the search worker, a reindex operation, and admin status before switching query reads.
