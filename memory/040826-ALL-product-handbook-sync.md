# 040826-ALL-product-handbook-sync

Sector: Cross-sector product specification and engineering documentation  
Agent: ChatGPT repository handbook synchronization  
Date: 04-08-2026  
Branch/Commit: `docs/product-handbook-sync-2026-08-04` based on `dcf8d5cd3d18bb29dccb70dbce44405043a8adcb`

## What changed

- Added `docs/PRODUCT_SPEC_AND_ENGINEERING_HANDBOOK.md` as the rolling reconciliation of approved MVP scope, current implementation, drift, and dependency-ordered remediation.
- Added `docs/audits/product-spec-audit-2026-08-04.md`.
- Updated the docs index to include the handbook and audit.
- Preserved `docs/00-ground-truth-mvp-spec.md` as the narrow normative MVP authority.

## Decisions / ADR notes

- Decision: the ground-truth MVP spec remains authoritative for approved scope; the new handbook is authoritative for current implementation status, evidence, drift, and rolling maintenance.
- Decision: historical 2026-06-29 smoke results are retained as E2 evidence, but current HEAD and production remain unverified.
- Decision: open issues #2–#10 are represented as required changes, not as proof that the complete VOD loop is absent.

## Validation

- Documentation-only review through the GitHub repository connector.
- Reviewed authoritative branch metadata, repository instructions, MVP/rollout/operational docs, core API models/routes/services, web upload/watch/admin surfaces, worker task/repository/storage, Compose, Make targets, CI workflow, smoke script, historical validation memory, open issues, and open PR state.
- Current repository tests were not executed because no runnable checkout/runtime was available in the connector environment.

## Files touched

- `docs/PRODUCT_SPEC_AND_ENGINEERING_HANDBOOK.md`
- `docs/audits/product-spec-audit-2026-08-04.md`
- `docs/README.md`
- `memory/040826-ALL-product-handbook-sync.md`

## Handoff / risks

- Implement Phase 1 from the handbook before worker/storage hardening: admin authorization, unlisted listing semantics, response-contract redaction, strict Clerk `azp`, and stale UI copy.
- Rerun `make test`, `make lint`, and `make smoke` on the branch before treating current-head validation as green.
- Production revision and deployment topology remain unverified.
