# API and Database Contract

Status: Sector B foundation  
Last updated: 28-06-2026

## Database Access

- SQLAlchemy async ORM is the application database boundary.
- `app.db.session.get_session` yields one `AsyncSession` per request.
- Service functions own commits for MVP route operations; callers should not keep ORM objects across requests.
- Alembic owns schema evolution. Run `make db-upgrade` after starting Postgres or before using video routes on a clean database.
- `DATABASE_URL` may use `postgresql://` in Compose env files; the API and Alembic convert it to `postgresql+asyncpg://`.

## Domain Tables

- `users` stores Clerk identity with `clerk_user_id`; no password fields exist.
- `videos` stores owner, privacy, canonical lifecycle status, media metadata, storage keys, and failure fields.
- `video_renditions` stores one row per generated HLS rendition.
- `video_processing_jobs` stores durable worker job attempts.
- `playback_events` is present for later player observability.

## Route Boundaries

- Sector B implements metadata CRUD, processing status, job records, playback metadata shape, and admin query skeletons.
- Sector C owns upload completion and original object writes.
- Sector D owns worker job execution and rendition population.
- Sector E owns the real HLS object proxy behind `GET /videos/{video_id}/hls/{path}`.
- Sector F owns replacing the dev identity headers with real Clerk JWT verification.
