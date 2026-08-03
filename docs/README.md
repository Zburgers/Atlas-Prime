# Atlas Prime Documentation

These documents define and track Atlas Prime, a learning-oriented, from-scratch video-on-demand platform.

## Canonical read order

1. `docs/00-ground-truth-mvp-spec.md` — narrow normative authority for approved MVP scope, locked architecture choices, privacy defaults, and the intended VOD lifecycle.
2. `docs/PRODUCT_SPEC_AND_ENGINEERING_HANDBOOK.md` — rolling source of truth for current implementation status, product-versus-code drift, evidence, known limitations, open rulings, and dependency-ordered remediation.
3. `docs/audits/product-spec-audit-2026-08-04.md` — adversarial audit establishing the first handbook baseline against authoritative commit `dcf8d5cd3d18bb29dccb70dbce44405043a8adcb`.
4. `docs/01-agent-operating-contract.md` — rules every implementation agent must follow.
5. `docs/02-owner-evaluation-and-rollout-guide.md` — original dependency order, review gates, and acceptance criteria; use the handbook for current completion status.
6. `docs/sectors/*.md` — sector-specific implementation manifests.
7. `memory/README.md` and `memory/_TEMPLATE.md` — required handoff and ADR protocol.

## Source-of-truth contract

- The ground-truth MVP spec governs what Atlas Prime is approved to become during the MVP.
- The product and engineering handbook governs the reconciled view of what is actually implemented, what contradicts the approved product rules, what remains unverified, and what should be implemented next.
- Executable code, migrations, tests, configuration, and attributable runtime evidence outrank descriptive claims about implementation state.
- Sector documents remain authoritative for narrow interfaces only when they do not conflict with the MVP spec or newer handbook evidence.
- Historical decisions and memory entries are preserved; superseded decisions should be marked rather than erased.

## Current audited state — 2026-08-04

The upload → MinIO → Celery/FFmpeg → HLS → API proxy → browser playback loop is implemented and has historical local smoke evidence. Current-head tests and any production deployment remain unverified.

The first remediation phase is the authorization and contract boundary:

1. define and enforce a real operator/admin role;
2. exclude unlisted videos from public discovery;
3. remove storage keys and queue identifiers from normal API responses;
4. require a matching Clerk `azp` when authorized parties are configured;
5. remove stale implementation-phase language from the product UI.

See the handbook for the complete phased plan covering upload/job idempotency, atomic HLS publication, deletion fencing, storage cleanup, segment integrity, telemetry governance, and release evidence.

## Sector map

| Sector | Manifest | Primary responsibility |
|---|---|---|
| A | `docs/sectors/A-product-web-app-shell.md` | Web shell, creator/watch UX, visible states |
| B | `docs/sectors/B-core-api-database.md` | API contracts, database schema, domain state machine |
| C | `docs/sectors/C-upload-ingest-storage.md` | API-mediated uploads, file validation, original media storage |
| D | `docs/sectors/D-media-processing-packaging.md` | FFmpeg/ffprobe, transcoding, HLS output generation |
| E | `docs/sectors/E-delivery-playback-cdn.md` | API-proxied HLS playback, player events, CDN pathing |
| F | `docs/sectors/F-auth-access-control.md` | Clerk identity, ownership, private-by-default playback access |
| G | `docs/sectors/G-observability-admin-ops.md` | Logs, metrics, admin status, operational visibility |
| H | `docs/sectors/H-testing-devex-ci.md` | Local dev, test harness, CI, smoke validation |

## Locked MVP defaults

- Stack: Next.js, FastAPI, SQLAlchemy/Alembic, PostgreSQL, Redis/Celery, Clerk, MinIO, FFmpeg/ffprobe, hls.js.
- Privacy: new and ready videos default to `private`; owners can later choose `public` or `unlisted`.
- Upload: browser uploads go through FastAPI, which validates and writes originals to MinIO.
- Playback: hls.js loads API-owned HLS URLs served by a FastAPI proxy over MinIO objects.

## Maintenance workflow

For future handbook refreshes:

1. establish the latest authoritative branch SHA;
2. read the existing handbook completely;
3. inspect code, tests, migrations, configuration, open issues/PRs, and deployment evidence;
4. update the same handbook in place;
5. append change history and preserve decision IDs;
6. create a dated audit when material drift is found;
7. write exactly one repository memory handoff;
8. validate and publish documentation-only changes through review.
