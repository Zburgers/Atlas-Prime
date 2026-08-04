# 050826-F-contract-boundary-tests

Sector: F auth/access control (Plan 1 Task 1.1)
Agent: Codex subtask agent
Date: 05-08-2026
Branch/Commit: local working tree; parent agent will commit

## What changed
- Added regression coverage for anonymous and signed-in non-owner exclusion of unlisted videos from listings.
- Added direct-link metadata and playback assertions for ready unlisted videos.
- Added non-admin 403 coverage across core admin, analytics, and moderation router families.

## Decisions / ADR notes
- Decision: Keep `ATLAS_ADMIN_CLERK_USER_IDS` as the operator identity source.
- Reason: This task locks the existing authorization contract before response-boundary refactoring.

## Validation
- `docker compose run --rm --build api pytest tests/test_video_api.py tests/test_clerk_auth.py tests/test_recommendation_logging.py -q` (43 passed)
- `docker compose run --rm --build api pytest tests/test_analytics_aggregates.py tests/test_moderation.py -q` (5 passed)
- `git diff --check` passed.

## Files touched
- `apps/api/tests/test_video_api.py`
- `apps/api/tests/test_recommendation_logging.py`
- `apps/api/tests/test_analytics_aggregates.py`
- `apps/api/tests/test_moderation.py`

## Handoff / risks
- Tests intentionally cover authorization gates only; no implementation changes were made.
- Parent should include this memory entry or consolidate its factual validation into the phase handoff entry.
