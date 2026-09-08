# Current-Head Release Evidence Implementation Plan

> **For implementation agents:** Use `shipyard:shipyard-executing-plans` and execute task IDs strictly in order.

**Goal:** Produce attributable repository and CI evidence for one exact candidate SHA without claiming an unverified production deployment.

**Architecture:** Add immutable build metadata to API/web images, expose a non-secret revision endpoint, make CI smoke self-contained, and qualify one exact head through local and GitHub gates. Deployment remains a separately approved operation.

**Tech Stack:** Docker Compose, GitHub Actions, FastAPI, Next.js, Make, pytest, shell smoke.

---

## Entry Gate

Plans 1-4 are COMPLETE with evidence SHAs. Working tree is preserved and the candidate head is recorded. Read Sectors G and H plus `docs/local-dev.md`. This plan verifies; it does not authorize deployment, release publication, or branch merge.

<task id="5.1" name="Fix self-contained CI Clerk configuration">
  <description>Resolve the failure observed in PR #11 run 30856956679 where web smoke never became ready because Clerk publishable key was absent.</description>
  <files>
    <modify>.github/workflows/ci.yml</modify>
    <modify>scripts/smoke-devex.sh</modify>
    <modify>apps/web/app/layout.tsx</modify>
    <modify>apps/web/tests/smoke.test.js</modify>
  </files>
  <steps>
    <step>Write a web test for smoke/dev-auth startup with no real Clerk secret.</step>
    <step>Implement the selected CI-only mechanism: when an explicit CI smoke-mode flag is enabled, render the local dev-auth shell without ClerkProvider; normal local and production modes remain Clerk-backed and fail closed when Clerk configuration is absent.</step>
    <step>Never embed a real key, enable dev auth by default, or weaken normal Clerk-backed startup.</step>
    <step>Run the exact local smoke environment used by CI.</step>
  </steps>
  <verification>
    <command>make smoke</command>
    <expected>PASS with no production Clerk secret and ATLAS_ALLOW_DEV_AUTH_HEADERS scoped to smoke only</expected>
  </verification>
</task>

<task id="5.2" name="Embed immutable build revision">
  <description>Make an image/runtime attributable to its source revision without exposing secrets.</description>
  <files>
    <modify>apps/api/Dockerfile</modify>
    <modify>apps/web/Dockerfile</modify>
    <modify>compose.yaml</modify>
    <modify>.env.example</modify>
    <modify>apps/api/app/core/config.py</modify>
  </files>
  <steps>
    <step>Add ATLAS_BUILD_SHA and ATLAS_BUILD_TIME build arguments/environment values; default local value is unknown.</step>
    <step>Pass exact git SHA from CI and documented build commands.</step>
    <step>Do not derive runtime truth from mutable branch names or local filesystem access.</step>
  </steps>
  <verification>
    <command>ATLAS_BUILD_SHA=$(git rev-parse HEAD) docker compose config</command>
    <expected>Valid Compose configuration with exact candidate SHA resolved</expected>
  </verification>
</task>

<task id="5.3" name="Expose revision and migration metadata">
  <description>Add a non-secret endpoint suitable for local/deployment attribution.</description>
  <files>
    <modify>apps/api/app/main.py</modify>
    <modify>apps/api/app/schemas/videos.py</modify>
    <modify>apps/api/tests/test_health_contract.py</modify>
    <modify>scripts/smoke-devex.sh</modify>
  </files>
  <steps>
    <step>Add GET /version returning build SHA, build time, app environment, and expected Alembic head; no host path, token, or storage credential.</step>
    <step>Add tests for configured and unknown local values.</step>
    <step>Make smoke assert reported SHA equals ATLAS_BUILD_SHA used for the candidate.</step>
  </steps>
  <verification>
    <command>docker compose run --rm --build api pytest tests/test_health_contract.py -q</command>
    <expected>PASS; revision response is exact and secret-free</expected>
  </verification>
</task>

<task id="5.4" name="Qualify one exact local candidate head">
  <description>Run all local gates once at an unchanged SHA and preserve their result.</description>
  <files>
    <create>docs/audits/release-evidence-current.md</create>
  </files>
  <steps>
    <step>Record candidate SHA and dirty-state snapshot before validation.</step>
    <step>Run lint, test, and smoke without changing files between commands.</step>
    <step>Record command, timestamp, exit result, reported /version SHA, and any environment-only caveat.</step>
    <step>If any command fails, stop; do not relabel the candidate qualified.</step>
  </steps>
  <verification>
    <command>make lint &amp;&amp; make test &amp;&amp; make smoke</command>
    <expected>All PASS at the same unchanged git SHA</expected>
  </verification>
</task>

<task id="5.5" name="Obtain attributable GitHub Actions evidence">
  <description>Verify the remote candidate, not merely a historical or local run.</description>
  <files>
    <modify>docs/audits/release-evidence-current.md</modify>
  </files>
  <steps>
    <step>Push/open/update the candidate PR only when owner authorization for publication exists.</step>
    <step>Use gh pr checks and gh run view to verify check headSha equals the candidate SHA.</step>
    <step>Record run URL, workflow, conclusion, and head SHA; pending is not green.</step>
    <step>Do not override failing required checks for a release qualification.</step>
  </steps>
  <verification>
    <command>gh pr checks &lt;candidate-pr&gt; &amp;&amp; test "$(gh pr view &lt;candidate-pr&gt; --json headRefOid -q .headRefOid)" = "$(git rev-parse HEAD)"</command>
    <expected>All required checks PASS and remote head equals local candidate SHA</expected>
  </verification>
</task>

<task id="5.6" name="Close release-evidence sequence">
  <description>Reconcile docs without inventing production evidence.</description>
  <files>
    <modify>docs/local-dev.md</modify>
    <modify>docs/PRODUCT_SPEC_AND_ENGINEERING_HANDBOOK.md</modify>
    <modify>docs/plans/README.md</modify>
    <create>memory/DDMMYY-GH-release-evidence.md</create>
  </files>
  <steps>
    <step>Update current-head evidence and CI state using exact SHAs and links.</step>
    <step>Leave production status UNVERIFIED unless an approved runtime was actually inspected.</step>
    <step>Create exactly one memory entry for this agent handoff.</step>
    <step>Mark Plan 5 COMPLETE only after Tasks 5.4 and 5.5 are green at one SHA.</step>
  </steps>
  <verification>
    <command>git diff --check &amp;&amp; rg -n "UNVERIFIED|candidate SHA|run URL" docs/audits docs/PRODUCT_SPEC_AND_ENGINEERING_HANDBOOK.md</command>
    <expected>Docs distinguish local, CI, and production evidence; index has exact completion SHA</expected>
  </verification>
</task>

## Stop Conditions

- Publication, PR creation, release, merge, and deployment require their own owner authorization if not already supplied.
- A green local run cannot substitute for green CI; a green CI run cannot prove deployment.
- Any file change after qualification creates a new candidate SHA and restarts Tasks 5.4-5.5.
