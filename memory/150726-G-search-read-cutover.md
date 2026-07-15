# 150726-G-search-read-cutover

Sector: G - Observability, Admin, and Search
Agent: Codex
Date: 15-07-2026
Branch/Commit: docs/fullplatform-rollout (pending commit)

## What changed
- Routed PostgreSQL-backed production search requests through Meilisearch candidate ranking when configured.
- Hydrated each candidate from PostgreSQL and retained only public, ready, approved videos in Meilisearch rank order.
- Added PostgreSQL fallback when Meilisearch is unavailable or returns invalid result data.

## Decisions / ADR notes
- Decision: use Meilisearch for candidate ranking, with PostgreSQL as the authorization and canonical response source.
- Reason: prevents stale index entries from exposing ineligible videos and keeps a durable fallback path.
- Alternatives considered: return indexed documents directly; rejected because index lag could violate public eligibility guarantees.

## Validation
- Focused API tests for Meilisearch hydration and PostgreSQL fallback.
- Live API request to `/search?q=smoke` after reindexing returned the indexed public video through the configured Meilisearch backend.
- API `/healthz` reported healthy Meilisearch dependency.

## Files touched
- `apps/api/app/services/search.py`
- `apps/api/tests/test_search.py`
- `docs/local-dev.md`
- `docs/plans/02-fullplatform-vision.md`

## Handoff / risks
- The index rebuild deletes then repopulates one index, so a concurrent search can temporarily return no candidate results; PostgreSQL fallback covers only service failure, not an empty but healthy index. A future zero-downtime design can use an alias or index swap.
- Phase 5 S2 transcript search remains deferred until caption documents are included in the search schema.
