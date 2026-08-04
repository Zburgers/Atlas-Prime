# 050826-F-clerk-authorized-party

Sector: F authentication and access control  
Agent: plan1_task14  
Date: 05-08-2026  
Branch/Commit: docs/fullplatform-rollout (local commit pending)

## What changed
- Clerk JWT verification now rejects a missing or non-string `azp` claim whenever `CLERK_AUTHORIZED_PARTIES` is configured.
- Token and configured-party values are trimmed and trailing-slash normalized before comparison.
- Added regression coverage for missing, mismatched, normalized matching, and empty allowlist behavior.

## Decisions / ADR notes
- Decision: Keep `ATLAS_ADMIN_CLERK_USER_IDS` as the operator identity source; this task only tightens Clerk authorized-party validation.
- Reason: A configured authorized-party allowlist must fail closed to prevent tokens from an unexpected frontend origin.
- Alternatives considered: None; issuer, signature, session-state, and dev-header behavior remain unchanged.

## Validation
- `docker compose run --rm --build api pytest tests/test_clerk_auth.py -q` (5 passed)

## Files touched
- `apps/api/app/services/auth.py`
- `apps/api/tests/test_clerk_auth.py`

## Handoff / risks
- Parent agent should cherry-pick or include the local commit; do not push from this task.
- An empty `CLERK_AUTHORIZED_PARTIES` intentionally preserves legacy optional `azp` behavior and should remain an explicit deployment choice.
