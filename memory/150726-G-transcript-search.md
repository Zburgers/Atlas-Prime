# 150726-G-transcript-search

Sector: G - Observability, Admin, and Search
Agent: Codex
Date: 15-07-2026
Branch/Commit: docs/fullplatform-rollout (pending commit)

## What changed
- Added bounded, markup-free WebVTT extraction to the public-video search index worker.
- Indexed caption text in each eligible Meilisearch video document and returned matching plain-text snippets from `/search`.
- Displayed matching caption snippets on public search cards.

## Decisions / ADR notes
- Decision: retain captions inside their parent video document instead of introducing a separate transcript index.
- Reason: preserves the existing public-video eligibility and one-result-per-video search contract.
- Alternatives considered: separate caption documents; deferred until cross-video transcript ranking needs separate pagination.

## Validation
- Focused API search/index tests, compilation, and frontend lint passed.
- Live caption upload, `make search-reindex`, Meilisearch query, and `/search` response verified the transcript phrase and snippet.
- `make test` (93 API tests, worker tests, web tests), `make lint`, and `make smoke` all passed.
- Mobile Chrome review at 375px confirmed the rendered transcript snippet is readable without clipping or overlap.

## Files touched
- `apps/api/app/services/search_index.py`
- `apps/api/app/services/search.py`
- `apps/api/app/worker/search.py`
- `apps/web/app/search/search-client.tsx`
- `docs/local-dev.md`

## Handoff / risks
- Reindexing is still whole-corpus replacement. Caption edits are reflected after the normal reindex command until incremental index updates are introduced.
