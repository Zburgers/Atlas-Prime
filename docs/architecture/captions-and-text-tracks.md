# Captions And Text Tracks

## Scope

Creators can upload one WebVTT caption track per language for each ready video. Tracks remain private media assets: neither storage keys nor direct MinIO URLs are returned to the browser.

## Data And Storage

`video_text_tracks` stores the video association, language, display label, default flag, content type, and internal storage key. The current MVP supports `kind=captions` only.

The worker-owned processed namespace holds the body:

```txt
processed/{video_id}/captions/{language}/{generated-name}.vtt
```

The path is an internal storage implementation detail, not a public API contract.

## API Contract

```txt
GET  /studio/videos/{video_id}/captions
POST /studio/videos/{video_id}/captions
GET  /videos/{video_id}/captions/{track_id}
```

Studio endpoints require the video owner. Caption delivery uses the same privacy checks as video playback, then streams `text/vtt` through FastAPI. `GET /videos/{video_id}/playback` returns API-owned track URLs in `text_tracks` for the player.

## Validation

- Only ready videos accept caption uploads.
- Uploads must be `.vtt`, `text/vtt` (or browser fallback `application/octet-stream`), begin with `WEBVTT`, and be at most 2 MiB.
- Language tags accept `en`, `eng`, and language-region values such as `en-US`.
- At most one caption track is marked default per video. The first track becomes default automatically; explicitly selecting another track replaces it.
