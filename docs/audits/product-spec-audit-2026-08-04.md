# Atlas Prime Product-Specification Grill Audit — 2026-08-04

Repository: `Zburgers/Atlas-Prime`  
Authoritative branch: `main`  
Verified commit: `dcf8d5cd3d18bb29dccb70dbce44405043a8adcb`  
Mode: `GRILL` followed by handbook synchronization  
Production revision: `UNVERIFIED`  
Current-head tests executed by this audit: no; connector-only documentation audit  
Historical validation reviewed: 2026-06-29 memory entry reporting API 28 passed, worker 2 passed, web 1 passed, lint passed, and end-to-end smoke passed

## Executive verdict

Atlas Prime has a real, integrated MVP vertical slice. Upload, storage, queue dispatch, media processing, HLS publication, API-authorized playback, browser playback, telemetry, local observability, and a Compose smoke harness are implemented.

The repository is not production-ready. The largest gap is no longer “finish HLS”; it is hardening the existing loop around authorization, privacy semantics, idempotency, job ownership, storage cleanup, deletion, telemetry governance, and release evidence.

## Finding A-001 — Admin authorization is not an admin boundary

Severity: **HIGH**  
Claim being challenged: `docs/observability-admin-ops.md` describes a protected admin portal.  
Document location: admin/ops documentation and Sector G assumptions.  
Actual implementation: every `/admin/*` route depends only on `CurrentUserDep`; any valid creator identity can list global videos/jobs/events and inspect worker/queue state. The web page checks sign-in only and the generic proxy adds no role policy.  
Evidence:

- `apps/api/app/api/admin.py`
- `apps/web/app/admin/page.tsx`
- `apps/web/app/admin/admin-dashboard.tsx`
- `apps/web/app/api/backend/[...path]/route.ts`

Why it matters: cross-user operational and media metadata becomes visible to all authenticated users.  
Correct classification: `⚠️ CHANGE`, evidence `E0` against the documented admin-protected claim.  
Recommended document correction: define the operator role as intended but currently absent.  
Recommended engineering action: implement explicit backend and Next.js/proxy role checks with signed-out/non-admin/admin tests.  
Confidence: **HIGH**

## Finding A-002 — Unlisted videos are publicly discoverable

Severity: **HIGH**  
Claim being challenged: unlisted videos are available by link but excluded from public listing/search.  
Document location: `docs/00-ground-truth-mvp-spec.md`, privacy section.  
Actual implementation: `list_visible_videos()` includes both `public` and `unlisted` ready videos in `public_ready`, including anonymous listing.  
Evidence: `apps/api/app/services/videos.py`.  
Why it matters: violates the core privacy contract and can expose link-only content.  
Correct classification: `⚠️ CHANGE`, evidence `E0`.  
Recommended engineering action: list only `public` ready video for non-owners; retain direct unlisted reads. Add owner/anonymous/non-owner tests.  
Confidence: **HIGH**

## Finding A-003 — Normal API responses expose storage and queue internals

Severity: **MEDIUM**  
Claim being challenged: clients should receive API-owned playback interfaces and should not depend on MinIO internals.  
Document location: ground-truth API/playback/security rules.  
Actual implementation: `VideoResponse` exposes original/master/thumbnail keys, `RenditionResponse` exposes playlist keys, and upload response exposes storage key plus Celery task ID. Public/unlisted responses use the same model.  
Evidence:

- `apps/api/app/schemas/videos.py`
- `apps/web/app/components/video-api.ts`
- `apps/api/tests/test_video_api.py`

Why it matters: internal topology becomes a stable public contract and leaks operational identifiers.  
Correct classification: `❌ REMOVE` from normal response contracts; retain only in admin/debug schema after admin authorization exists.  
Confidence: **HIGH**

## Finding A-004 — Upload is not race-safe

Severity: **MEDIUM**  
Claim being challenged: upload status transitions and queue dispatch are reliable.  
Actual implementation: status `uploading` is accepted as an uploadable state; no compare-and-set, lock, idempotency key, or active-job uniqueness protects two concurrent requests.  
Evidence: `apps/api/app/services/uploads.py`; open issue #4.  
Impact: overwritten originals, duplicate jobs, conflicting failed/success states.  
Correct classification: `⚠️ CHANGE`.  
Recommended action: atomic claim from draft/failed, idempotency token, one active job, concurrent integration test.  
Confidence: **HIGH**

## Finding A-005 — Celery redelivery can race without attempt ownership

Severity: **MEDIUM**  
Claim being challenged: durable job attempts safely survive worker failure.  
Actual implementation: late acknowledgements are enabled, while worker repository updates are unconditional and lack a lease/generation token or stale-running recovery.  
Evidence:

- `workers/media/media_worker/celery_app.py`
- `workers/media/media_worker/repository.py`
- open issue #6

Correct classification: `⚠️ CHANGE`.  
Recommended action: attempt claim/lease, compare-and-set transitions, bounded retries, stale reaper, duplicate/redelivery tests.  
Confidence: **HIGH**

## Finding A-006 — Failed HLS publication leaves partial objects

Severity: **MEDIUM**  
Claim being challenged: failed processing produces a clean failed state.  
Actual implementation: object upload is sequential and exception handling only updates database failure state; storage abstraction has no cleanup.  
Evidence: worker `celery_app.py`, `storage.py`; open issue #7.  
Impact: orphaned/mixed-generation objects and permanent storage growth.  
Correct classification: `⚠️ CHANGE`.  
Recommended action: attempt-specific staging and publish-on-success, or tracked cleanup.  
Confidence: **HIGH**

## Finding A-007 — Video deletion is database-only

Severity: **MEDIUM**  
Claim being challenged: successful delete removes a video.  
Actual implementation: service deletes the ORM row and commits; object storage has no delete operation.  
Evidence: `apps/api/app/services/videos.py`; open issue #8.  
Impact: retained user media and orphaned storage after 204.  
Correct classification: `⚠️ CHANGE`.  
Recommended action: durable deletion workflow with retryable cleanup and explicit completion semantics.  
Confidence: **HIGH**

## Finding A-008 — Active worker can recreate media after deletion

Severity: **MEDIUM**  
Claim being challenged: deletion is authoritative.  
Actual implementation: no tombstone, revoke tracking, generation fence, or worker existence check occurs before download/upload/finalize.  
Evidence: API delete service, worker task/repository; open issue #9.  
Correct classification: `⚠️ CHANGE`.  
Recommended action: deletion state plus generation fencing and race tests.  
Confidence: **HIGH**

## Finding A-009 — HLS segment authorization is filename-pattern based

Severity: **MEDIUM**  
Claim being challenged: HLS proxy serves only generated output.  
Actual implementation: playlists/thumbnail are exact-key checked; segments only require a valid rendition label, `segment_` prefix, and allowed suffix.  
Evidence: `_resolve_hls_asset()` in `apps/api/app/api/videos.py`; open issue #5.  
Correct classification: `⚠️ CHANGE`.  
Recommended action: persist/derive segment inventory or use generation-specific unguessable prefixes.  
Confidence: **HIGH**

## Finding A-010 — Anonymous playback telemetry is unbounded

Severity: **MEDIUM**  
Claim being challenged: playback events are an observability feature.  
Actual implementation: every valid readable-video request creates a permanent row; no rate limit, event/session ID, deduplication, sampling, or retention exists.  
Evidence: event route, model; open issue #10.  
Correct classification: `⚠️ CHANGE`.  
Recommended action: rate limit, deduplicate, aggregate/sample, and expire.  
Confidence: **HIGH**

## Finding A-011 — Authorized-party allowlist accepts a missing `azp`

Severity: **MEDIUM**  
Claim being challenged: configured Clerk authorized parties constrain accepted tokens.  
Actual implementation: rejection occurs only when both allowlist and token `azp` are present.  
Evidence: `apps/api/app/services/auth.py`; open issue #3.  
Correct classification: `⚠️ CHANGE`.  
Recommended action: when allowlist is non-empty, require a matching `azp`.  
Confidence: **HIGH**

## Finding A-012 — Planning and rollout docs are stale relative to implementation

Severity: **LOW**  
Claim being challenged: the owner checklist accurately reflects remaining work.  
Actual implementation: the checklist remains entirely unchecked and old copy still describes D/E HLS work as pending, while the repository contains worker/proxy implementation and a recorded full smoke pass. Issue #1 also still says the HLS path must be finished.  
Evidence:

- `docs/02-owner-evaluation-and-rollout-guide.md`
- `apps/web/app/watch/[videoId]/watch-client.tsx`
- `memory/290626-H-wave3-integration-smoke.md`
- issue #1

Correct classification: documentation/backlog drift.  
Recommended action: use the new handbook as the rolling status artifact; update/close stale backlog separately after owner review.  
Confidence: **HIGH**

## Finding A-013 — Deployment and current-head validation are not proven

Severity: **INFORMATIONAL**  
Claim being challenged: none; evidence gap.  
Actual implementation: Compose and CI definitions exist, but this audit found no attributable production revision and did not execute current-head tests. Historical local validation is recorded.  
Correct classification: runtime `UNVERIFIED`; do not mark any feature E1.  
Recommended action: rerun current-head validation and add revision metadata before any production claim.  
Confidence: **HIGH**

## Classification summary

- Major capabilities classified `✅ SHIPPED`: 9
- Required `⚠️ CHANGE` items: 10
- Required `❌ REMOVE` items: 2
- Approved `🔨 BUILD` items: 0 independent product features
- Candidate groups: 8
- Open rulings: 4
- Existing open issues incorporated: #2 through #10
- Stale issue identified: #1

## Recommended first implementation phase

Start with the authorization and contract boundary:

1. real operator/admin authorization;
2. unlisted discovery correction;
3. storage/queue identifier redaction;
4. strict Clerk `azp`;
5. stale user-facing HLS copy removal.

This phase has the highest risk reduction and creates safer contracts before schema-heavy worker/storage remediation.
