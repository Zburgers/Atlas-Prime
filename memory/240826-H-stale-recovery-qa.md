# 240826-H-stale-recovery-qa

Sector: H testing/devex/ci
Agent: Luna QA
Date: 24-08-2026
Branch/Commit: docs/fullplatform-rollout / 0ca718ea5f10dfa37224c6b01ad477fe05ea96d5

## What changed
- Added a focused recovery test for a successful job fence followed by a zero-row video fence.
- Made the recovery session fake model savepoint rollback and observable job/video state.

## Decisions / ADR notes
- Decision: Verify second-fence atomicity in the existing unit-test seam.
- Reason: A real savepoint must not leave the job failed when the matching video transition is no longer applicable.
- Alternatives considered: No production or live-database changes were permitted for this QA remediation.

## Validation
- `pytest -q tests/test_processing_recovery.py` - 10 passed.
- `python -m compileall -q app tests` - passed.
- `git diff --check` - passed.

## Files touched
- `apps/api/tests/test_processing_recovery.py`
- `memory/240826-H-stale-recovery-qa.md`

## Handoff / risks
- The new test proves the fake restores the job to `running`, leaves video failure state unchanged, reports no recovered job, and performs no retry path after the second fence fails.
- Live PostgreSQL concurrency and savepoint qualification remain deployment-level risks; production code was intentionally not modified.
- Frontend and Hallmark/design/accessibility work was not touched.
