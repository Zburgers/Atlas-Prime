# WebVTT captions

Sector: C upload/storage and E delivery/playback
Agent: Codex
Date: 12-07-2026
Branch/Commit: docs/fullplatform-rollout

## What changed
- Added owner-managed WebVTT caption tracks for ready videos, including metadata, migration, MinIO-backed processed storage, and API-owned delivery.
- Added caption URLs to playback metadata and native browser caption tracks on the watch page.
- Added the Studio caption upload/listing surface, rollout plan entry, architecture contract, and API regression coverage.

## Decisions / ADR notes
- Decision: Store captions as `video_text_tracks` and proxy them through FastAPI rather than publishing object URLs.
- Reason: Caption access must follow the video's privacy policy and must not reveal internal MinIO keys.
- Alternatives considered: Direct browser-to-MinIO delivery was rejected because it bypasses the existing API-owned media boundary.

## Validation
- `docker compose run --rm --build api alembic upgrade head`
- `docker compose run --rm --build api pytest tests/test_captions.py tests/test_thumbnails.py tests/test_video_api.py -q` (27 passed)
- `npm --workspace apps/web run build`
- `make lint` and `make test` (all API, worker, and web checks passed)
- `make smoke` reached successful stack startup but failed after HLS upload on a pre-existing worker `KeyError: 0` in thumbnail-selection completion logic; remediation is tracked as a separate follow-up commit.

## Files touched
- `apps/api/app/api/captions.py`
- `apps/api/app/services/captions.py`
- `apps/api/alembic/versions/20260712_0010_video_text_tracks.py`
- `apps/web/app/watch/[videoId]/watch-client.tsx`
- `apps/web/app/studio/videos/[videoId]/caption-manager.tsx`

## Handoff / risks
- One `captions` track per language is supported; the initial scope does not include subtitles, chapters, editing, deletion, or AI generation.
- Worker smoke currently fails independently of captions after packaging media because the thumbnail completion code indexes a mapping result positionally.
