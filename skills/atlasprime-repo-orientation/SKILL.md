---
name: atlasprime-repo-orientation
description: Orient agents to AtlasPrime's services, entry points, contracts, and safe working workflow before repository changes.
---

# AtlasPrime repository orientation

Use this skill at the beginning of any AtlasPrime task when the relevant service, route, worker, data flow, or validation command is not already familiar. It is a repository map, not a substitute for current code or runtime evidence.

## Fast path

1. Check the checkout before reading or changing code:

   ```sh
   git status --short --branch
   git log -1 --oneline --decorate
   git diff --stat
   ```

   Preserve existing tracked and untracked work. Do not reset, clean, stash, overwrite, or broadly format an active worktree. Reconcile any map entry with the current diff before relying on it.

2. Read the [system map](references/system-map.md) for the service topology, HTTP and web entry points, background jobs, data flows, and validation routes.

3. Read the canonical documents in this order: [MVP spec](../../docs/00-ground-truth-mvp-spec.md), [engineering handbook](../../docs/PRODUCT_SPEC_AND_ENGINEERING_HANDBOOK.md), [plan index](../../docs/plans/README.md), the relevant [sector manifest](../../docs/sectors/), then the nearest [memory handoffs](../../memory/).

4. Treat the plan index as the only implementation queue. The full-platform vision and historical memory explain intent and evidence but do not authorize skipping the current entry gate.

5. Choose the narrowest repeatable validation for the touched boundary. Use `make test`, `make lint`, focused tests, or alternate-port `make smoke` as appropriate; separate local/CI evidence from authenticated browser, deployment, and production claims.

6. Before handoff, create exactly one dated file under `memory/` using [`memory/_TEMPLATE.md`](../../memory/_TEMPLATE.md), record the exact files and validation, and report any remaining worktree or runtime risks.

## Routing

- Upload, processing, publication, deletion, or storage: start with the upload-to-playback flow and sectors B/C/D/E, then read the processing/deletion runbook.
- Auth, privacy, admin, or playback access: start with the auth chain and sectors E/F/G; never infer authorization from the Next proxy alone.
- Search, feed, discovery, engagement, Studio, captions, playlists, or analytics: use the corresponding API route/service and web surface in the system map, then verify current schemas/tests.
- Framework, SDK, API, CLI, or cloud-service changes: follow the repository's latest-official-documentation rule before editing.

Do not assume a green historical commit means the current checkout or deployed runtime is green. In particular, inspect the worktree for in-flight files before running broad tests or claiming a plan/release gate.
