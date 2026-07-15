# 150726-G-search-index-worker

Sector: G - Observability, Admin, and Search
Agent: Codex
Date: 15-07-2026
Branch/Commit: docs/fullplatform-rollout (pending commit)

## What changed
- Added the dedicated Celery `search-worker` and a public-video Meilisearch rebuild task.
- Added an admin-only reindex endpoint and `make search-reindex` operational command.
- Rebuilds now replace the entire indexed corpus with public, ready, approved videos so stale documents are removed.

## Decisions / ADR notes
- Decision: keep public search reads on PostgreSQL while Meilisearch is populated asynchronously.
- Reason: preserves the established search behavior while the dedicated read cutover is validated.
- Alternatives considered: immediate search read cutover; deferred to the next Phase 5 slice.

## Validation
- `make test` (90 API tests, worker tests, web tests)
- `make lint`
- `make smoke`
- Live `make search-reindex`; verified the healthy search worker rebuilt the Meilisearch index with one public document.

## Files touched
- `apps/api/app/services/search_index.py`
- `apps/api/app/worker/search.py`
- `apps/api/app/api/admin.py`
- `compose.yaml`
- `docs/local-dev.md`

## Handoff / risks
- The public `/search` and admin search-debug reads intentionally remain on PostgreSQL until dedicated-read behavior and relevance are validated.
- Index rebuild is a replacement operation; avoid routing reads to Meilisearch during a rebuild without a later alias/swap strategy.
