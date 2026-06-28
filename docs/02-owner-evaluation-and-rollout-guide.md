# Owner Evaluation and Rollout Guide

Status: instructions for the human engineering owner  
Purpose: decide work order, evaluate sector output, and keep the project coherent.

## 1. Recommended implementation waves

### Wave 0 — foundation

Start these first:

| Sector | Why first |
|---|---|
| H — Testing/DevEx/CI | Creates repeatable local startup and validation surface. |
| B — Core API/Database | Defines domain objects, status machine, and contracts. |
| F — Auth/Access Control | Establishes user ownership and security model early. |

Wave 0 should produce a bootable skeleton even if media processing is not working yet.

### Wave 1 — core VOD loop

Then run:

| Sector | Depends on | Goal |
|---|---|---|
| C — Upload/Ingest/Storage | B, F, H | Store original uploaded media safely. |
| D — Media Processing/Packaging | B, C, H | Convert uploaded media to HLS. |
| A — Product/Web Shell | B, F, H | Show upload/list/watch/status UX, initially with mocks if needed. |

Wave 1 should make the core path visible, even if rough.

### Wave 2 — playback and operational hardening

Then run:

| Sector | Depends on | Goal |
|---|---|---|
| E — Delivery/Playback/CDN | B, C, D, F | Play generated HLS in browser through clean playback URLs. |
| G — Observability/Admin/Ops | B, C, D, E, H | Make failures debuggable and processing state visible. |

Wave 2 should make the MVP reliable enough to demo.

### Wave 3 — integration hardening

Finally, do integration passes:

- Upload a known-good sample video.
- Upload a bad/corrupt file.
- Upload as user A and verify user B cannot mutate it.
- Delete/reprocess a video if supported.
- Restart worker mid-job and verify failure/retry behavior.
- Confirm memory entries exist for all sector work.

## 2. Dependency graph

```txt
H Testing/DevEx/CI
  -> all sectors

B Core API/Database
  -> C Upload/Ingest
  -> D Processing
  -> E Playback
  -> G Admin/Ops

F Auth/Access Control
  -> A Product UX
  -> C Upload/Ingest
  -> E Playback

C Upload/Ingest/Storage
  -> D Processing
  -> E Delivery

D Media Processing/Packaging
  -> E Playback
  -> G Observability

A Product/Web Shell
  -> integrates B/C/E/F/G

G Observability/Admin/Ops
  -> reads signals from B/C/D/E/H
```

## 3. Sector independence rules

Parallelize only where interfaces are stable.

Safe early parallel work:

- A can build UI against mocked API responses.
- H can build local scripts and sample media fixtures.
- B can define schema and endpoint contracts.
- F can define auth middleware and ownership checks.

Avoid parallelizing these too early:

- D before C defines storage layout.
- E before D defines HLS output path.
- G before B defines job/video schema.

## 4. System-level acceptance criteria

Do not call the MVP done until all of these are true:

- [ ] Clean checkout starts locally with documented commands.
- [ ] Database migrations apply cleanly.
- [ ] User can sign up or log in.
- [ ] User can create a video record.
- [ ] User can upload a small MP4.
- [ ] Original media is stored in the expected storage layout.
- [ ] Worker can probe the original file.
- [ ] Worker can generate at least 720p and 360p HLS outputs where source quality allows.
- [ ] `master.m3u8` is generated.
- [ ] Thumbnail is generated.
- [ ] Video status transitions to `ready`.
- [ ] Watch page plays the video in a modern desktop browser.
- [ ] Bad/corrupt upload reaches a visible `failed` state.
- [ ] User A cannot edit/delete/process User B's video.
- [ ] Logs show enough information to debug failed processing.
- [ ] Tests/smoke checks exist for critical path.
- [ ] Every sector has at least one `memory/` entry.

## 5. Per-sector review checklist

When reviewing an agent's sector output, check:

- Did it stay in MVP scope?
- Did it read and respect the main spec?
- Did it document any changed interface?
- Did it update dependent docs if necessary?
- Did it add tests or a repeatable smoke check?
- Did it add a short `memory/` entry?
- Did it avoid hardcoded secrets and local-only absolute paths?
- Did it fail safely?

## 6. Integration smoke test target

The repo should eventually expose one command or documented flow equivalent to:

```bash
# suggested final shape; exact commands may differ
cp .env.example .env
docker compose up --build
make migrate
make seed-sample-user
make smoke-video
```

The smoke test should verify:

1. API health.
2. DB connectivity.
3. Queue connectivity.
4. Worker online.
5. Sample video can be processed.
6. HLS output exists.
7. Playback manifest endpoint returns expected data.

## 7. Decision escalation guide

Agents can decide independently on:

- Internal function names.
- Component structure.
- Test organization.
- Small implementation details that do not affect cross-sector contracts.

Agents must escalate or record ADR-level decisions for:

- Stack changes.
- Database schema changes.
- Video lifecycle/status changes.
- Storage layout changes.
- Playback URL/auth changes.
- Queue/job payload changes.
- Docker/local command changes.

## 8. Suggested branch/task naming

```txt
sector/A-web-shell
sector/B-video-schema
sector/C-upload-storage
sector/D-hls-worker
sector/E-playback
sector/F-auth-ownership
sector/G-admin-observability
sector/H-devex-ci
```

## 9. What to postpone aggressively

Keep these out until the first VOD loop works:

- Adaptive recommendation feed.
- Live ingest.
- Low-latency streaming.
- CDN vendor-specific tuning.
- DRM.
- Payments.
- Creator monetization.
- Multi-region object storage.
- Kubernetes.
- GPU transcoding.
- Complex moderation workflows.

## 10. Final handoff package expected from agents

For each sector, expect:

- Implementation diff.
- Tests/smoke notes.
- Memory entry.
- Known issues.
- Next recommended sector action.
