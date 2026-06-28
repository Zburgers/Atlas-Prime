# Atlas Prime Planning Artifacts

These documents define the initial engineering foundation for Atlas Prime, a learning-oriented, from-scratch video streaming platform.

## Read order

1. `docs/00-ground-truth-mvp-spec.md` — canonical product and architecture scope.
2. `docs/01-agent-operating-contract.md` — rules every implementation agent must follow.
3. `docs/02-owner-evaluation-and-rollout-guide.md` — dependency order, review gates, and acceptance criteria for the human engineering owner.
4. `docs/sectors/*.md` — sector-specific implementation manifests.
5. `memory/README.md` and `memory/_TEMPLATE.md` — required minimal changelog / ADR protocol.

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

## Project stance

This is intentionally VOD-first and learning-first. The MVP should teach the full path from upload to HLS playback without prematurely building live streaming, DRM, recommendations, payments, or a large distributed system.

## Locked MVP defaults

- Stack: Next.js, FastAPI, SQLAlchemy/Alembic, PostgreSQL, Redis/Celery, Clerk, MinIO, FFmpeg/ffprobe, hls.js.
- Privacy: new and ready videos default to `private`; owners can later choose `public` or `unlisted`.
- Upload: browser uploads go through FastAPI, which validates and writes originals to MinIO.
- Playback: hls.js loads API-owned HLS URLs served by a FastAPI proxy over MinIO objects.
