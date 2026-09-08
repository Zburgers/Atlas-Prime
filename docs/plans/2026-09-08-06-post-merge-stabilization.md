# Plan 6 — Post-Merge Stabilization

> **For implementation agents:** This is the only executable stabilization roadmap after PR #12. Use Shipyard discipline: each implementation slice below is one coherent PR, planned against a fresh `main`, with an explicit approach, strongest rejected alternative, ordered file anchors, tests, verification obligations, exact-head CI, and an independent gate before merge. Do not combine slices into another mega-PR.

Status: **READY**
Planned against: `main` at `50e3f325c5e07376c4b703312d3f422d7ecd572c` (PR #12 merge commit)
Date: 2026-09-08
Issues in scope: #2, #19, #24, #22, #18
Owner decisions inherited: D-011, D-012, D-013; R-001 remains unresolved

## Goal

Stabilize the merged Atlas Prime platform at its highest-risk remaining security, media-resource, playback-I/O, health-check, and original-object lifecycle boundaries **without adding product features or redesigning the stack**.

Plan 6 is complete only when:

1. server-side web/admin authorization independently denies non-admin access while FastAPI remains authoritative;
2. decoded-media work is rejected before expensive FFmpeg work according to an owner-approved media envelope;
3. HLS proxy delivery does not perform synchronous object-store reads on the FastAPI event loop or buffer whole segments in memory;
4. deep readiness checks have bounded fan-out, deadlines, off-loop blocking I/O, and short-lived single-flight caching while liveness remains cheap;
5. superseded/orphan-prone original uploads have durable, idempotent cleanup and reconciliation;
6. each issue has focused regression evidence and exact-head green CI on its own PR;
7. the final Plan 6 exit gate passes from a clean checkout of current `main`.

## Why these five issues

These are the remaining open findings closest to Atlas Prime's core trust and VOD loop after PR #12:

- **#2 — admin authorization:** the FastAPI admin dependency is authoritative, but the Next `/admin` page and `/api/backend/admin/*` proxy do not independently enforce D-011.
- **#19 — decoded media complexity:** the upload byte cap does not bound decoded duration/resolution/frame-rate work; exact limits are not owner-approved.
- **#24 — HLS streaming:** the async HLS route currently calls synchronous boto3 and materializes the full object body before responding.
- **#22 — readiness isolation:** `/healthz` performs multiple dependency checks per request, sequentially, including synchronous MinIO access.
- **#18 — original cleanup:** a retry with a different original extension can supersede the DB pointer while leaving the previous object behind; failure after object write can also orphan data.

This plan intentionally excludes #14–#17, Recommendation V2/ML, product expansion, deployment, production qualification, analytics rebuild scalability, and migration-at-container-startup. Those require separate plans or later promotion.

## Architecture

Plan 6 keeps the existing stack and contracts:

- **Auth:** Clerk remains identity provider. `ATLAS_ADMIN_CLERK_USER_IDS` remains the single operator allowlist source (D-011). FastAPI remains authoritative; the web boundary adds defense in depth.
- **Media:** `ffprobe` remains the cheap admission/probe step and FFmpeg remains the processor. A bounded research spike is required before numeric media limits are implemented because R-001 and the decoded-media envelope are not owner decisions today.
- **Delivery:** Keep boto3/MinIO and the API-owned HLS proxy. Fix blocking/buffering with thread offload + streaming; do not add an async S3 dependency unless the planned approach is proven impossible.
- **Health:** Keep `/healthz/live` cheap. Deep dependency readiness uses concurrent bounded checks and an in-process short TTL/single-flight cache; it must not depend on Redis merely to cache Redis's own health result.
- **Original storage:** Keep the canonical `originals/{video_id}/source.{ext}` key layout. Add durable cleanup intent/reconciliation instead of redesigning original object naming across sectors.

## Shipyard execution contract

Shipyard's unit of executable work is one coherent PR. Plan 6 therefore has five implementation PRs plus one **research-only spike** for #19.

For every child slice:

1. Start from a freshly fetched `origin/main`; record the exact base SHA in the task/PR.
2. Re-read:
   - `docs/00-ground-truth-mvp-spec.md`
   - `docs/01-agent-operating-contract.md`
   - this plan
   - the named sector manifests
   - recent relevant `memory/` entries
   - latest official docs for touched frameworks/libraries.
3. Verify the issue premise still exists in current code. If already fixed/superseded, stop and close/shelve with evidence rather than reimplementing it.
4. Produce/confirm a PR-sized spec with:
   - chosen approach;
   - strongest rejected alternative and why;
   - exact file anchors;
   - acceptance tests;
   - a **verification obligation** for each activated risk.
5. Red test first where practical; implement the smallest change that discharges the obligation.
6. Run focused tests, then `make lint`, `make test`, and `make smoke` unless the slice explicitly documents a narrower reason.
7. Add exactly one relevant `memory/DDMMYY-SECTOR-short-topic.md` handoff.
8. Push and require:
   - PR head == CI-green commit;
   - independent gate/re-review is pinned to that same commit;
   - any post-review fix resets the gate.
9. Close the linked GitHub issue only after the exact final implementation is evidenced.
10. **Stop before merge.** Merge remains an owner action/authorization.

Do not run child implementation slices concurrently when they touch the same file/contracts. #24 must land before #22 so the health work can reuse the object-store timeout/offload primitive instead of creating a second S3 policy.

---

<task id="6.1" issue="#2" title="Server-side admin authorization">

### Scope

Add a real server-side authorization boundary to the Next.js admin page and admin backend proxy while preserving FastAPI `AdminUserDep` as the final authority.

### Required grounding

- Sector F — Authentication and Access Control
- Sector G — Observability, Admin, and Operations
- Current Clerk Next.js App Router server-auth documentation

### Current seam

- `apps/web/app/admin/page.tsx` renders `AdminDashboard` with no server guard.
- `apps/web/app/api/backend/[...path]/route.ts` is a generic transport proxy and does not locally authorize `/admin/*`.
- `apps/api/app/api/deps.py` already enforces D-011 with `ATLAS_ADMIN_CLERK_USER_IDS`.
- `apps/web/proxy.ts` runs Clerk middleware outside exact CI smoke mode.

### Chosen approach

Create one server-only web admin policy helper that:

1. obtains the Clerk `userId` with current server-side Clerk APIs;
2. parses the same `ATLAS_ADMIN_CLERK_USER_IDS` allowlist contract as FastAPI;
3. distinguishes unauthenticated from authenticated-non-admin;
4. is called by the `/admin` Server Component **before** the dashboard renders;
5. is called by the catch-all backend Route Handler **only when the first proxied path segment is `admin`**, before any upstream request is made.

Expected response semantics:

- signed out: redirect to sign-in for the page; `401` for admin proxy calls;
- signed in, not allowlisted: do not render admin UI; `403` for admin proxy calls;
- allowlisted: render/proxy normally;
- FastAPI still repeats the authoritative admin check.

Do **not** introduce Clerk Organizations, a new role table, custom JWT claims, or a second operator identity source.

### Strongest rejected alternative

**Rely only on FastAPI because it already protects `/admin/*`.**

Rejected: it leaves privileged UI/data requests crossing the web server boundary before role authorization and does not close #2's defense-in-depth requirement. The API remains authoritative, but the web boundary must deny early too.

### Files

Expected anchors; adapt only for minor path drift:

- `apps/web/app/admin/page.tsx`
- `apps/web/app/api/backend/[...path]/route.ts`
- new server-only helper under `apps/web/app/` or `apps/web/lib/`
- `apps/web/tests/smoke.test.js` and/or a minimal test file using the existing Node test runner
- `compose.yaml` — pass `ATLAS_ADMIN_CLERK_USER_IDS` to the web runtime
- `.env.example` — clarify that the same allowlist is consumed by API + web
- relevant auth/admin docs if behavior text becomes stale

### Implementation steps

1. Add a pure allowlist parser/policy function separate from Clerk I/O so empty, whitespace, duplicate, allow/deny cases are directly testable without secrets.
2. Add a server-only Clerk wrapper that calls the current `auth()` API and feeds `userId` to the policy.
3. Guard `app/admin/page.tsx` before `AdminDashboard` is created.
4. In the backend catch-all Route Handler, identify `path[0] === "admin"` and run the same policy before computing/issuing upstream `fetch`.
5. Keep all non-admin proxy routes behaviorally unchanged.
6. Add the web runtime env wiring; do not expose the allowlist through `NEXT_PUBLIC_*`.
7. Preserve `ATLAS_CI_SMOKE_MODE` as a CI shell/auth-provider bypass only. It must **not** become an admin authorization bypass in normal code.
8. Add regression evidence.

### Verification obligations

| Risk | Claim | Named evidence |
|---|---|---|
| Authentication | Signed-out clients cannot render admin or proxy admin traffic | focused web policy/route tests + optional Clerk-backed browser checkpoint |
| Authorization | Authenticated non-admin is denied before upstream fetch | focused test proving `fetch` is not invoked for denied admin path |
| Positive path | D-011 allowlisted `userId` can render/proxy | focused policy/wiring test; Clerk-backed manual checkpoint when credentials are available |
| Defense in depth | FastAPI admin enforcement remains unchanged | existing API admin tests pass |
| Secret boundary | Allowlist stays server-only | source/build check: no `NEXT_PUBLIC_ATLAS_ADMIN...` |
| Regression | Non-admin backend proxy paths are unchanged | focused proxy test/source assertion + web build |

### Focused verification

```sh
docker compose run --rm --build web-test npm --workspace apps/web test
docker compose build web
docker compose run --rm --build api pytest tests/test_admin.py tests/test_clerk_auth.py
```

If the exact API admin test filename differs, select the current files containing `AdminUserDep` denial/allowance coverage and record the path drift.

### Exit

- #2 acceptance behavior is evidenced.
- one Sector F/G memory entry exists.
- exact-head CI + gate green.
- #2 may be closed.
</task>

---

<task id="6.2" issue="#19" title="Bounded decoded-media policy spike">

**Kind: RESEARCH ONLY. No production limit implementation is authorized in this task.**

### Why a spike is required

The repository requires upload size limiting, but R-001 still says agents must not invent a new maximum upload size. More importantly, Atlas Prime currently has **no owner-approved decoded-media envelope** for duration, effective dimensions/pixel area, frame rate, or decoded-work budget.

The worker currently probes duration and dimensions, then transcodes admitted media. Numeric limits would therefore be a product/operations decision, not a safe implementation detail.

Use the bounded protocol in:

`docs/research/2026-09-08-media-complexity-admission-spike.md`

### Research questions

Answer only these:

1. Which `ffprobe` fields reliably provide:
   - duration;
   - width/height;
   - display rotation/effective dimensions;
   - `avg_frame_rate` / fallback frame rate;
   - missing/non-finite values?
2. At what point in the current worker can admission reject the source after one probe and before any thumbnail/transcode FFmpeg command?
3. What CPU/wall-time/peak-memory behavior does the current local worker show for a small, bounded fixture matrix?
4. Which 2–3 candidate media envelopes are reasonable for Atlas Prime's single-node learning MVP?
5. Should Compose-level worker memory/CPU limits be part of #19 remediation or a later deployment/ops plan?

### Required evidence

- exact commands and environment;
- fixture generation commands, not large committed binaries;
- ffprobe JSON excerpts for orientation/fps edge cases;
- timing + peak-memory table;
- candidate policy table with tradeoffs;
- proposed owner decision **D-014** containing explicit numeric values and missing/invalid metadata behavior;
- explicit statement that R-001 upload-byte policy is unchanged unless separately decided.

### Spike stop condition

Do **not** edit worker admission code or choose numeric limits inside the spike. End with status `NEEDS OWNER DECISION: D-014`.

Tasks 6.3–6.5 may proceed after this research artifact is merged because they do not depend on D-014. Task 6.6 may not start until D-014 is explicitly approved and recorded.
</task>

---

<task id="6.3" issue="#24" title="Nonblocking streamed HLS proxy">

### Scope

Remove synchronous S3 I/O and whole-object buffering from the FastAPI HLS proxy without changing playback authorization, path allowlisting, signed-delivery semantics, or the storage key contract.

### Required grounding

- Sector E — Delivery, Playback, and CDN Pathing
- Sector F — access rules
- current Starlette/FastAPI streaming-response behavior
- current boto3/botocore S3 `get_object`, `StreamingBody`, timeout, and retry docs

### Chosen approach

Keep boto3. Split "open object" from "consume object":

- object-store `get_object` is executed off the event loop;
- the storage service returns metadata plus a closable streaming body/iterator rather than `bytes`;
- FastAPI returns `StreamingResponse`;
- stream reading is bounded by a fixed chunk size and blocking iteration is thread-offloaded by the response machinery or explicit iterator adapter;
- the body is closed in `finally`/disconnect cleanup;
- S3 connect/read timeouts and standard bounded retries are explicit/configurable;
- existing ETag, Content-Length, Content-Type and Cache-Control behavior is preserved.

Use one shared S3 client-config helper if both processed/original storage paths need identical transport policy.

### Strongest rejected alternative

**Replace boto3 with aioboto3/another async S3 client.**

Rejected for this stabilization slice: it adds a dependency and changes storage lifecycle semantics across API paths when bounded thread offload + `StreamingBody` directly addresses the event-loop and memory defect.

### Files

- `apps/api/app/services/storage.py`
- `apps/api/app/api/videos.py`
- `apps/api/app/core/config.py` if timeout/retry config lives there
- `.env.example`
- `compose.yaml`
- `apps/api/tests/test_storage.py`
- `apps/api/tests/test_playback_delivery.py` and/or `apps/api/tests/test_video_api.py`

### Implementation steps

1. Add explicit S3 transport config:
   - connect timeout;
   - read timeout;
   - standard retry mode with a bounded total-attempt count.
   Defaults must be conservative local operational defaults and configurable; do not use an unbounded retry loop.
2. Replace `HlsObject.body: bytes` with a streaming contract that preserves object metadata and owns a closable response body.
3. Offload the initial synchronous `get_object` call from the FastAPI event loop.
4. Return `StreamingResponse` for proxied HLS media. Use a bounded constant chunk size (recommended `256 KiB` unless focused evidence shows a reason to change it).
5. Guarantee close on normal completion, read failure, and client disconnect/cancellation.
6. Preserve existing `404`/authorization/path-inventory semantics.
7. Do not alter signed redirect mode except to reuse safe client configuration.
8. Add regressions.

### Verification obligations

| Risk | Claim | Named evidence |
|---|---|---|
| Event loop | slow S3 open/read does not serialize unrelated async requests | async regression with delayed fake storage + concurrent lightweight request |
| Memory | segment response is streamed, not materialized as one `bytes` body | fake multi-chunk body test + source contract |
| Cleanup | underlying `StreamingBody` closes on success/failure/disconnect path | fake closable-body tests |
| HTTP contract | content type/length/etag/cache headers remain correct | playback delivery tests |
| Security | authorization + inventory/path traversal fences are unchanged | existing playback/access regression suite |
| Failure bound | S3 connection/read behavior has explicit timeouts/retries | config tests |

### Focused verification

```sh
docker compose run --rm --build api pytest \
  tests/test_storage.py \
  tests/test_playback_delivery.py \
  tests/test_video_api.py
```

### Exit

- #24 reproduced by a pre-fix test and disproved after implementation.
- one Sector E memory entry.
- exact-head CI + gate green.
- #24 may be closed.
</task>

---

<task id="6.4" issue="#22" title="Bounded and isolated dependency readiness">

### Scope

Make deep readiness bounded under dependency slowness/outage without changing `/healthz/live` into a dependency probe.

### Required grounding

- Sector G — Observability/Admin/Ops
- Sector H — Testing/CI
- current asyncio timeout/concurrency behavior
- reuse the S3 timeout/offload primitive landed by 6.3

### Chosen approach

- Keep `/healthz/live` as the constant-time API-process liveness signal.
- Keep `/healthz` as deep readiness.
- Run Postgres, Redis, MinIO, and configured search checks concurrently.
- Give every check a deadline and enforce an overall readiness deadline.
- Run MinIO's boto3 call off the event loop.
- Add a short in-process TTL cache with single-flight refresh so bursts of probes do not fan out to every dependency.
- On timeout/failure, return a sanitized `degraded` dependency result; never expose credentials/URLs/stack traces.

The cache must use monotonic time. Defaults should be small and configurable (recommended starting point: 2-second result TTL, 2-second per-check timeout, 3-second overall deadline) and must be validated against existing Compose healthcheck timing.

### Strongest rejected alternative

**Cache readiness in Redis.**

Rejected: Redis is itself one of the dependencies under test. Making the health endpoint depend on Redis to retrieve/cache the result couples failure handling to the component whose failure it is supposed to report.

### Files

- `apps/api/app/main.py` (or extract a small health service if it reduces coupling)
- `apps/api/app/core/config.py`
- `.env.example`
- `compose.yaml` only if health config/env wiring changes; keep API service healthcheck on `/healthz/live`
- `apps/api/tests/test_health_contract.py`

### Implementation steps

1. Extract dependency check callables only as far as needed for isolated tests.
2. Use concurrent execution rather than the current sequential chain.
3. Wrap each dependency check in explicit timeout/error normalization.
4. Offload MinIO S3 call using the shared transport/offload pattern from 6.3.
5. Implement in-process cached result + async single-flight refresh.
6. Preserve `ATLAS_HEALTH_SKIP_DEPENDENCIES=true` semantics.
7. Keep `/healthz/live` untouched by dependency state.
8. Add regressions for delay, timeout, concurrency, cache/single-flight and sanitization.

### Verification obligations

| Risk | Claim | Named evidence |
|---|---|---|
| Bounded latency | one hung dependency cannot hang `/healthz` past the configured overall bound | delayed fake dependency timing test |
| Fan-out | N concurrent health requests trigger one refresh window, not N×dependency calls | counter-based concurrency test |
| Event loop | sync MinIO access is off-loop | delayed MinIO fake + concurrent liveness test |
| Liveness | `/healthz/live` stays 200 regardless of deep dependency state | existing + new test |
| Privacy | errors contain component/status, not endpoint/secret/exception internals | sanitization test |
| Compose | service health remains based on `/healthz/live` | Compose config assertion |

### Focused verification

```sh
docker compose run --rm --build api pytest tests/test_health_contract.py
docker compose config -q
```

### Exit

- #22 acceptance behavior is evidenced.
- one Sector G/H memory entry.
- exact-head CI + gate green.
- #22 may be closed.
</task>

---

<task id="6.5" issue="#18" title="Durable cleanup of superseded original uploads">

### Scope

Prevent retry uploads from silently leaving superseded/orphaned original objects while preserving the canonical original-object key layout and upload/job state machine.

### Required grounding

- Sector B — DB/status contracts
- Sector C — Upload, Ingest, Storage
- existing Plan 3 tombstone/deletion reconciliation pattern
- current upload generation/idempotency contracts

### Chosen approach

Introduce a narrow durable **original-object cleanup intent**:

- when a retry writes a new object whose key differs from the currently authoritative `video.original_storage_key`, the transaction that makes the new key authoritative also records the old key for cleanup;
- after commit, cleanup is attempted;
- failed cleanup remains durable and retryable;
- a reconciler processes pending/failed intents in bounded batches;
- before deletion, the reconciler re-checks that the candidate key is **not** the current authoritative original key;
- failure after storing a new object but before DB publication triggers compensating delete; if that delete fails while DB is available, record cleanup intent after rollback.

Keep `originals/{video_id}/source.{ext}`. Do not switch the whole system to attempt-scoped original keys in this slice.

### Strongest rejected alternative

**Delete the previous object inline after updating the DB and only log failures.**

Rejected: once the DB pointer has moved, a failed delete loses the durable reference to the superseded key and recreates the privacy/storage orphan that #18 exists to fix.

Also rejected: **redesign every original as an attempt-scoped key**. That is a wider Sector C/D storage-contract migration and is unnecessary to close this issue.

### Expected files

- new Alembic migration for cleanup intent table
- `apps/api/app/db/models.py`
- new service such as `apps/api/app/services/original_cleanup.py`
- `apps/api/app/services/uploads.py`
- `apps/api/app/services/storage.py` only if interface adjustment is necessary
- new bounded reconciliation command under `apps/api/app/commands/`
- `Makefile` dry-run/apply reconciliation target
- `apps/api/tests/test_video_api.py` and/or a new focused cleanup test
- schema/storage docs + `.env.example` only if new config is introduced

### Data contract

The cleanup intent must minimally retain:

- stable intent ID;
- `video_id`;
- object key;
- status (`pending`, `running`/claimed if needed, `complete`, `failed`);
- attempt count;
- last sanitized error;
- created/updated timestamps.

Uniqueness/idempotency must prevent duplicate work for the same video/key while allowing a completed historical record.

The cleanup worker/command must never delete a key that currently equals `video.original_storage_key`.

### Implementation steps

1. Write failing tests for different-extension retry and post-write failure orphaning.
2. Add migration/model.
3. Capture the previous authoritative key during the existing locked upload claim/publication flow.
4. In the same DB transaction that publishes the new original pointer, persist cleanup intent for a superseded different key.
5. After commit, attempt cleanup without rolling back a successful upload if cleanup fails.
6. Add bounded idempotent reconciliation, dry-run by default; require explicit `--apply` for deletion.
7. Add compensation for object-written/DB-not-published failure.
8. Reuse sanitized error/log conventions.
9. Add tests for retries and safety fence.

### Verification obligations

| Risk | Claim | Named evidence |
|---|---|---|
| Privacy/storage | different-extension retry leaves no untracked superseded object | fake storage integration test |
| Safety | reconciler never deletes the current authoritative object | same-key/current-key fence test |
| Durability | cleanup failure survives as retryable DB state | failure injection test |
| Idempotency | repeated reconciliation is safe and converges | repeated-run test |
| Transaction failure | object written before DB failure is compensated or durably recorded | failure injection test |
| Operator safety | reconciliation is bounded and destructive mode is explicit | CLI dry-run/apply tests |

### Focused verification

```sh
docker compose run --rm --build api pytest \
  tests/test_video_api.py \
  tests/test_video_deletion.py
docker compose run --rm --build api alembic upgrade head
```

Add the new focused test filename to the command once created.

### Exit

- #18 acceptance behavior is evidenced.
- one Sector B/C memory entry.
- exact-head CI + gate green.
- #18 may be closed.
</task>

---

<task id="6.6" issue="#19" title="Decoded-media admission remediation">

### Entry gate

**HARD BLOCK:** D-014 from task 6.2 must be explicitly owner-approved and recorded with numeric values and metadata-failure semantics.

If D-014 is absent or ambiguous, stop. Do not infer limits from fixtures, upload bytes, common streaming-provider limits, FFmpeg timeout, or this document.

### Scope

Reject media that exceeds D-014 **immediately after the one authoritative `ffprobe` result and before any thumbnail/transcode FFmpeg command**.

This does not change R-001 unless the owner separately changes upload-byte policy.

### Chosen approach

1. Expand `MediaProbe` to normalize:
   - finite positive duration;
   - encoded dimensions;
   - display rotation/effective dimensions;
   - finite rational frame rate, preferring the D-014-approved source field/fallback;
   - any derived work metric approved in D-014.
2. Add worker config getters for every approved limit with strict parsing/fail-fast configuration semantics.
3. Add a pure `validate_media_policy(probe, policy)` step.
4. Invoke it after `probe_media()` and before rendition planning, thumbnail generation, or package FFmpeg invocation.
5. Surface a stable, sanitized processing failure code such as `MEDIA_POLICY_REJECTED` plus a non-sensitive reason category (`duration`, `dimensions`, `frame_rate`, `metadata`) without echoing raw ffprobe output to users.
6. Preserve deterministic job failure/fencing/publication behavior.

### Strongest rejected alternative

**Use `ATLAS_FFMPEG_TIMEOUT_SECONDS` as the resource limit.**

Rejected: a timeout only kills work after CPU/memory has already been consumed and does not bound decoded-frame complexity or concurrency pressure. Admission must happen before expensive FFmpeg work.

### Expected files

- `workers/media/media_worker/packager.py`
- `workers/media/media_worker/config.py`
- `workers/media/media_worker/celery_app.py` and/or repository failure mapping
- `workers/media/tests/test_packager.py`
- `workers/media/tests/test_repository.py` if failure-state mapping changes
- `.env.example`
- `compose.yaml`
- Sector D/media docs
- D-014 decision location named by the research spike

### Required tests

For every D-014 dimension:

- exactly at limit: admitted;
- just over limit: rejected;
- missing/non-finite/zero/negative metadata: behaves exactly as D-014 says;
- rotated portrait/landscape fixture: effective dimensions handled correctly;
- rational/fractional fps: parsed deterministically;
- rejection test proves packaging/thumbnail FFmpeg subprocess is **not invoked**;
- known-good small fixture still reaches HLS package path.

If the spike approves Compose worker resource limits, add them here with explicit local defaults and validation. If not, leave them for a later ops/deployment plan; do not smuggle them in.

### Verification obligations

| Risk | Claim | Named evidence |
|---|---|---|
| Pre-FFmpeg admission | over-limit source launches no expensive FFmpeg work | subprocess-spy regression |
| Policy fidelity | every D-014 boundary is exact | at/over parameterized tests |
| Rotation/fps | effective geometry/rate cannot bypass policy | ffprobe parser fixtures |
| Failure UX | user gets stable sanitized failure | repository/task failure test |
| Config | malformed/missing required non-dev policy fails safely | config tests |
| MVP regression | normal fixture still packages | worker focused suite + Sector H smoke |

### Focused verification

```sh
docker compose run --rm --build worker pytest tests/test_packager.py tests/test_repository.py
make worker-test
```

### Exit

- #19 implementation matches D-014 exactly.
- one Sector D memory entry.
- exact-head CI + gate green.
- #19 may be closed.
</task>

---

<task id="6.7" title="Plan 6 exit and ledger reconciliation">

### Entry gate

- 6.1, 6.3, 6.4, 6.5 are merged.
- 6.2 research is merged.
- 6.6 is merged only after D-014; if owner explicitly defers D-014/#19, Plan 6 must remain `PARTIAL`, not `COMPLETE`.

### Steps

1. Verify issue states:
   - #2 closed only with server-side web auth evidence;
   - #24 closed only with streamed/off-loop HLS evidence;
   - #22 closed only with bounded readiness evidence;
   - #18 closed only with durable cleanup evidence;
   - #19 closed only after approved D-014 remediation.
2. Run from clean, current `main`:

```sh
make lint
make test
make smoke
git diff --check
```

3. Run the plan-index completeness check from `docs/plans/README.md`; expected no output.
4. Confirm no Plan 6 slice changed:
   - public/private/unlisted semantics;
   - D-013 telemetry contract;
   - canonical HLS/output key layout;
   - canonical original key layout;
   - R-001 upload-byte limit without an owner decision;
   - deployment/production status.
5. Add a final concise cross-sector memory handoff only if the final integrator changed docs/interfaces beyond the slice memories.
6. Update `docs/plans/README.md`:
   - Plan 6 state `COMPLETE`;
   - exact merge SHAs for all child PRs;
   - final whole-stack evidence SHA/run;
   - D-014 if approved.
7. Stop. Do not automatically promote #14–#17 or any feature roadmap.

### Final verification obligation

**Claim:** `main` contains all five bounded stabilizations, the full VOD loop still passes, and the evidence being recorded is for the exact current commit.

**Evidence:** clean-checkout whole-stack commands + exact-head CI + child issue/PR SHA table + independent final review.
</task>

## Global stop conditions

Stop and return to the owner if any of these occur:

- current `main` materially differs from the plan's stamped base in a touched contract before the first child is specced;
- an implementation slice requires a new auth identity source, storage layout, video status, public API shape, or queue/job contract not described here;
- #19 lacks D-014;
- a fix would require replacing Clerk, boto3/MinIO, FastAPI, Celery, or FFmpeg;
- a child uncovers a P1/P0 issue outside its scope that makes the planned approach unsafe;
- exact-head CI or the independent gate is red;
- a post-gate commit moves the PR head;
- work drifts into production deployment, Recommendation V2/ML, monetization, live streaming, native mobile, #14–#17, analytics rebuild scalability, or migration orchestration.

## Latest-docs anchors checked during planning

Planning research on 2026-09-08 verified the intended implementation seams against:

- current Clerk Next.js App Router server-side auth guidance (`auth()` in Server Components and Route Handlers);
- current FFprobe documentation for structured stream/format probing and selected entries;
- current boto3 S3 `get_object` contract (`StreamingBody`, content metadata);
- current botocore/boto3 client retry configuration guidance.

Agents must re-check current official docs at execution time if versions/base have materially moved.
