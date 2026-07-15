# Local Development

Sector H owns the repeatable local stack.

## Prerequisites

- Docker with Compose v2
- `make`
- Optional local `ffmpeg` for generating the sample media fixture outside containers

## Start

```sh
make env
clerk init --app app_3Fldg6OPLlGBAMmcAv2bDYuT0PD
make up
```

Run `clerk init` from `apps/web` if the CLI cannot detect Next.js from the monorepo root. The linked Clerk application is `app_3Fldg6OPLlGBAMmcAv2bDYuT0PD`.

Services:

| Service | URL |
|---|---|
| Web | http://localhost:3001 |
| API | http://localhost:8000 |
| API docs | http://localhost:8000/docs |
| MinIO console | http://localhost:9001 |
| Meilisearch | http://localhost:7700 |
| PostgreSQL | localhost:15432 |
| Redis | localhost:16379 |

MinIO local buckets are bootstrapped as private buckets:

- `atlas-originals`
- `atlas-processed`

Signed playback uses MinIO's explicit server CORS origins from `ATLAS_MEDIA_CORS_ALLOWED_ORIGINS` (default: `http://localhost:3001`). Set it to the exact browser origin or origins for each deployment. The bucket policies remain private, so browser access still requires a signed object URL; the CORS setting does not make either bucket public.

Phase 5 runs Meilisearch as the dedicated search service. Compose keeps it internal to API traffic except for the local port above. Set `MEILISEARCH_MASTER_KEY` to a 16+-character secret and `MEILI_ENV=production` outside local development. `ATLAS_SEARCH_BACKEND=meilisearch` makes the API dependency health endpoint report its availability. The `search-worker` rebuilds the index with public, ready, approved videos only and replaces the old document set, so content that loses public eligibility is removed. Search reads remain on the PostgreSQL implementation until the dedicated-read cutover is validated.

## Standard Commands

```sh
make test
make lint
make smoke
make search-reindex
make logs
make down
```

## Fixture Strategy

Generate a tiny synthetic MP4:

```sh
make fixture
```

The generated fixture is `fixtures/media/sample-2s.mp4` and is ignored by git.

## Smoke Coverage

`make smoke` validates:

- Compose config is valid.
- Full stack builds and starts with local smoke-only dev auth headers enabled.
- The API applies Alembic migrations before it starts serving traffic; `make db-upgrade` remains available for an explicit migration run.
- API `/healthz` can reach PostgreSQL, Redis, private MinIO buckets, and Meilisearch when enabled.
- Web responds on port 3000.
- API MVP contract metadata keeps `private` as the default privacy and documents API-mediated upload plus API-proxied HLS.
- Celery media worker responds to ping.
- The dedicated search worker is healthy.
- A known-good sample MP4 can be uploaded through FastAPI, stored in MinIO, processed by the worker, marked `ready`, and fetched through API-owned HLS manifest, rendition, segment, and thumbnail routes.
- A second user cannot mutate or play the private ready video.
- A corrupt MP4-shaped upload is accepted into the processing path, then reaches a visible `failed` state with a failure code.

`make smoke` temporarily exports `ATLAS_ALLOW_DEV_AUTH_HEADERS=true` for repeatable local integration checks. Leave that setting disabled for normal Clerk-backed development unless you are intentionally running local smoke/test flows.
