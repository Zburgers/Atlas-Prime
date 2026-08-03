# Contract Boundary Remediation Implementation Plan

> **For implementation agents:** Use `shipyard:shipyard-executing-plans` and execute task IDs strictly in order.

**Goal:** Close the remaining reachable authorization, privacy, response-boundary, Clerk-token, and stale-UI defects without changing playback or storage internals.

**Architecture:** Keep FastAPI as the authoritative authorization boundary and the Next proxy as a transport boundary. Split normal product schemas from operator/debug schemas so public and creator clients receive API-owned URLs and domain state, never MinIO keys or Celery identifiers.

**Tech Stack:** FastAPI, Pydantic, Clerk JWT, SQLAlchemy, Next.js App Router, pytest, Node test runner.

---

## Entry Gate

- Branch contains merged PR #11 and rollout commit `4f0e98d` or equivalent functionality.
- Read the required project set plus Sectors B, F, G, and A.
- `git status --short` is captured; unrelated user changes are preserved.
- Do not start Plan 2 until this plan's exit gate passes and the evidence commit is added to `docs/plans/README.md`.

<task id="1.1" name="Lock current admin and unlisted behavior with regression tests">
  <description>Turn already-delivered rollout behavior for C-001 and C-002 into explicit prerequisites before response refactoring.</description>
  <files>
    <modify>apps/api/tests/test_video_api.py</modify>
    <modify>apps/api/tests/test_clerk_auth.py</modify>
    <modify>apps/api/tests/test_recommendation_logging.py</modify>
  </files>
  <steps>
    <step>Add tests proving anonymous and non-owner listings exclude ready unlisted videos while direct-link read/playback remains allowed.</step>
    <step>Add tests proving a signed-in non-allowlisted user receives 403 from every admin router family.</step>
    <step>Run the focused tests and confirm existing implementation passes before refactoring.</step>
  </steps>
  <verification>
    <command>docker compose run --rm --build api pytest tests/test_video_api.py tests/test_clerk_auth.py tests/test_recommendation_logging.py -q</command>
    <expected>PASS; no unlisted discovery and no non-admin global-data access</expected>
  </verification>
</task>

<task id="1.2" name="Separate product and operator video schemas">
  <description>Remove internal storage keys and queue identifiers from normal public/creator contracts while retaining them in protected debug responses.</description>
  <files>
    <modify>apps/api/app/schemas/videos.py</modify>
    <modify>apps/api/app/api/videos.py</modify>
    <modify>apps/api/app/api/admin.py</modify>
    <modify>apps/api/tests/test_video_api.py</modify>
  </files>
  <steps>
    <step>Write assertions that normal create/list/detail/upload/playback responses omit original, HLS, thumbnail, rendition playlist storage keys and Celery task IDs.</step>
    <step>Introduce explicit operator/debug schema fields for those values; do not reuse the product response model.</step>
    <step>Update route serializers minimally and keep API-owned playback, thumbnail, caption, and delivery URLs unchanged.</step>
    <step>Run focused tests; inspect generated OpenAPI names for distinct schemas.</step>
  </steps>
  <verification>
    <command>docker compose run --rm --build api pytest tests/test_video_api.py tests/test_playback_delivery.py -q</command>
    <expected>PASS; product responses contain no storage key or Celery task ID</expected>
  </verification>
</task>

<task id="1.3" name="Update frontend types and callers for redacted contracts">
  <description>Remove client dependencies on fields deleted by Task 1.2 without changing user-visible playback behavior.</description>
  <files>
    <modify>apps/web/app/components/video-api.ts</modify>
    <modify>apps/web/app/upload/upload-form.tsx</modify>
    <modify>apps/web/app/studio/videos/studio-video-manager.tsx</modify>
    <modify>apps/web/app/admin/admin-dashboard.tsx</modify>
    <modify>apps/web/tests/smoke.test.js</modify>
  </files>
  <steps>
    <step>Delete normal-client fields for storage keys, rendition keys, upload storage key, and Celery task ID.</step>
    <step>Create a separate admin debug type only for fields returned by protected debug endpoints.</step>
    <step>Write/update Node smoke assertions for successful upload, Studio list, and admin debug rendering.</step>
    <step>Run web tests and build.</step>
  </steps>
  <verification>
    <command>docker compose run --rm --build web-test npm --workspace apps/web test &amp;&amp; docker compose run --rm --build web-test npm --workspace apps/web run build</command>
    <expected>PASS and successful Next.js production build</expected>
  </verification>
</task>

<task id="1.4" name="Require configured Clerk authorized party">
  <description>Close C-011 by failing closed when an authorized-party allowlist exists and the token has a missing or non-matching azp claim.</description>
  <files>
    <modify>apps/api/app/services/auth.py</modify>
    <modify>apps/api/tests/test_clerk_auth.py</modify>
  </files>
  <steps>
    <step>Add red tests for non-empty allowlist plus missing azp, mismatched azp, normalized matching azp, and empty allowlist.</step>
    <step>Change verification to reject when parties exist and normalized token azp is absent or not a member.</step>
    <step>Preserve issuer, signature, session-state, and dev-header behavior.</step>
  </steps>
  <verification>
    <command>docker compose run --rm --build api pytest tests/test_clerk_auth.py -q</command>
    <expected>PASS; configured allowlist rejects missing and mismatched azp</expected>
  </verification>
</task>

<task id="1.5" name="Remove stale watch-page implementation copy">
  <description>Close C-012 so the product UI describes current processing state rather than sector ownership history.</description>
  <files>
    <modify>apps/web/app/watch/[videoId]/watch-client.tsx</modify>
    <modify>apps/web/tests/smoke.test.js</modify>
  </files>
  <steps>
    <step>Add a test that rendered copy never contains “D/E still own HLS”.</step>
    <step>Replace it with user-safe status guidance based on queued, processing, ready, or failed state.</step>
    <step>Verify failed state still exposes only sanitized failure text.</step>
  </steps>
  <verification>
    <command>docker compose run --rm --build web-test npm --workspace apps/web test</command>
    <expected>PASS; no sector/process-internal language in watch UI</expected>
  </verification>
</task>

<task id="1.6" name="Document and close the contract-boundary phase">
  <description>Reconcile contract docs and record one attributable phase handoff.</description>
  <files>
    <modify>docs/api-database.md</modify>
    <modify>docs/observability-admin-ops.md</modify>
    <modify>docs/PRODUCT_SPEC_AND_ENGINEERING_HANDBOOK.md</modify>
    <modify>docs/plans/README.md</modify>
    <create>memory/DDMMYY-ABFG-contract-boundary.md</create>
  </files>
  <steps>
    <step>Document public/creator versus operator schemas and the environment-allowlist operator source.</step>
    <step>Update C-001, C-002, C-003, C-011, and C-012 branch status with evidence.</step>
    <step>Create exactly one memory entry for this agent handoff.</step>
    <step>Run the exit gate and write the evidence commit into the index.</step>
  </steps>
  <verification>
    <command>make lint &amp;&amp; make test &amp;&amp; make smoke &amp;&amp; git diff --check</command>
    <expected>PASS at one attributable commit; Plan 1 marked COMPLETE and Plan 2 READY</expected>
  </verification>
</task>

## Stop Conditions

- Any normal frontend caller genuinely requires an internal key: stop and define an API-owned capability instead of restoring the field.
- Admin identity source must remain `ATLAS_ADMIN_CLERK_USER_IDS` for this phase; changing to Clerk metadata/org claims is an ADR-level redesign requiring owner approval.
- Any private or unlisted access regression blocks promotion.
