# AGENTS.md — Agent Working Guide

## Prime Directive

Build only the MVP described in `docs/00-ground-truth-mvp-spec.md` unless the human owner (naki) explicitly expands scope.

Work follows this loop:
```
read spec
  -> inspect repo
  -> check relevant latest official docs
  -> make the smallest useful change
  -> validate
  -> write memory entry
  -> hand off clearly
```

## Required Reading Before Any Implementation

Every agent must read these documents before making code changes:

1. `docs/00-ground-truth-mvp-spec.md` - Canonical MVP scope and video lifecycle
2. `docs/01-agent-operating-contract.md` - Rules every implementation agent must follow
3. `memory/README.md` - Memory folder protocol
4. `memory/_TEMPLATE.md` - Required handoff entry format

For implementation-specific contracts, read your sector manifest under `docs/sectors/`.

## Memory Entry Requirement

**Before handoff, you MUST create exactly one markdown file under `memory/`** using the template.

### Filename Format
```
DDMMYY-SECTOR-short-topic.md
```

### Template Usage
Copy the structure from `memory/_TEMPLATE.md`. Every entry must include:
- Sector identifier
- Date
- What changed (minimal bullets)
- Decisions / ADR notes (use `No ADR-level decision.` if none)
- Validation (or `Not run` with explanation)
- Files touched (important paths only)
- Handoff / risks (what next agent needs to know)

### Memory Rules
- Keep entries short, factual, and searchable
- Do not overwrite another agent's entry
- Record cross-sector interface changes clearly
- Write one entry per meaningful handoff

## Scope Control

**Stay within MVP scope unless explicitly permitted.** The project intentionally excludes:
- Live streaming, DRM, recommendations, payments
- Mobile apps, complex moderation workflows
- Kubernetes, GPU transcoding, multi-region CDN
- Distributed autoscaling before single-node loop works

If a feature seems useful but is out of scope, record it as a future note in the memory entry, not as implementation.

## Interface Discipline

If your work changes any of these cross-sector interfaces, document it in your memory entry:
- API request/response shapes
- Video status values
- Database schema
- Storage paths
- HLS output layout
- Auth/session behavior
- Worker job payload
- Environment variables

## Validation Requirement

Leave behind at least one repeatable validation method:
- Unit tests
- Integration tests
- Smoke commands
- Manual browser checks with exact steps
- FFmpeg/ffprobe command output
- API request examples

If validation cannot run, explicitly write `Not run` in your memory entry with the reason.

## Secrets and Security

- Never commit secrets. Use environment variables.
- Never expose absolute filesystem paths in API responses
- Prevent path traversal in file operations
- Sanitize error messages for user safety
- Developer logs must include enough context (video_id, job_id, sector/stage)

## Confirmed Stack (MVP)

These choices are finalized for the MVP build:

- **Frontend**: Next.js (TypeScript/React)
- **API**: FastAPI with SQLAlchemy ORM
- **Database**: PostgreSQL (Dockerized) with Alembic migrations
- **Queue**: Redis + Celery
- **Auth**: Clerk (external provider, JWT-based)
- **Storage**: MinIO (S3-compatible, from day one)
- **Worker**: FFmpeg + ffprobe (Python-based worker)
- **Player**: hls.js

All agents must use these choices unless recording an ADR-level decision for alternatives.

## Essential Documentation Links

- Apple HLS: https://developer.apple.com/documentation/http-live-streaming
- FFmpeg: https://ffmpeg.org/documentation.html
- ffprobe: https://ffmpeg.org/ffprobe.html
- hls.js: https://github.com/video-dev/hls.js/
- Media Source Extensions: https://developer.mozilla.org/en-US/docs/Web/API/Media_Source_Extensions_API

When touching a framework/tool that may have changed, check the latest official documentation before implementing.