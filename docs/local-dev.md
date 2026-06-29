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
| PostgreSQL | localhost:15432 |
| Redis | localhost:16379 |

MinIO local buckets are bootstrapped as private buckets:

- `atlas-originals`
- `atlas-processed`

## Standard Commands

```sh
make test
make lint
make smoke
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
- Alembic migrations apply cleanly.
- API `/healthz` can reach PostgreSQL, Redis, and private MinIO buckets.
- Web responds on port 3000.
- API MVP contract metadata keeps `private` as the default privacy and documents API-mediated upload plus API-proxied HLS.
- Celery media worker responds to ping.
- A known-good sample MP4 can be uploaded through FastAPI, stored in MinIO, processed by the worker, marked `ready`, and fetched through API-owned HLS manifest, rendition, segment, and thumbnail routes.
- A second user cannot mutate or play the private ready video.
- A corrupt MP4-shaped upload is accepted into the processing path, then reaches a visible `failed` state with a failure code.

`make smoke` temporarily exports `ATLAS_ALLOW_DEV_AUTH_HEADERS=true` for repeatable local integration checks. Leave that setting disabled for normal Clerk-backed development unless you are intentionally running local smoke/test flows.
