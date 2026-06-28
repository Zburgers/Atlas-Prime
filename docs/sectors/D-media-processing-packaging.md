# Sector D — Media Processing and HLS Packaging

Owner: media/worker agent  
Primary mission: convert uploaded original media into browser-playable HLS outputs.

## Scope

Build the worker pipeline:

- Claim processing jobs.
- Probe source media with `ffprobe`.
- Store media metadata.
- Generate thumbnail.
- Generate HLS output with at least 720p and 360p renditions where possible.
- Write rendition records.
- Mark video `ready` or `failed`.
- Capture useful processing logs/errors.

## Out of scope

- GPU transcoding.
- Distributed/autoscaled worker pool.
- Live transcoding.
- DRM packaging.
- AV1/HEVC optimization.
- Complex per-title encoding ladder.

## Interfaces consumed

From Sector B:

- Processing job schema.
- Video status transitions.
- Rendition model.

From Sector C:

- Original source storage key/path.
- Storage service for reading original and writing processed outputs.

From Sector H:

- Local FFmpeg availability and sample media fixtures.

## Interfaces provided

To Sector E:

- HLS output layout.
- `master.m3u8` storage key.
- Rendition playlist keys.
- Thumbnail key.

To Sector G:

- Job timings.
- Worker logs.
- Failure codes/messages.

## Required output contract

```txt
processed/{video_id}/hls/
  master.m3u8
  720p/playlist.m3u8
  360p/playlist.m3u8
  thumbnail.jpg
```

Segment names should be deterministic and safe for static serving.

## FFmpeg/ffprobe behavior

The worker should:

1. Use `ffprobe` to inspect duration, streams, codecs, dimensions, bitrate, and frame rate where available.
2. Reject or fail gracefully when no valid video stream exists.
3. Avoid generating renditions larger than the source unless the decision is explicitly recorded.
4. Capture stderr/stdout logs in developer-visible logs, but sanitize user-facing errors.
5. Use timeouts/resource limits where feasible.

## Deliverables

- Worker process or command.
- Job claim/execute/update logic.
- Probe parser.
- FFmpeg HLS generation command(s).
- Thumbnail generation.
- Rendition DB writes.
- Failure handling and retry policy.
- Tests or smoke command using a small fixture video.

## Acceptance criteria

- [ ] Worker can process a known-good MP4 fixture.
- [ ] Worker writes `master.m3u8` and rendition playlists.
- [ ] Worker writes at least one playable segment per rendition.
- [ ] Worker generates thumbnail.
- [ ] Worker records duration/dimensions/codecs where available.
- [ ] Worker marks successful video as `ready`.
- [ ] Worker marks corrupt/unreadable source as `failed` with useful failure reason.
- [ ] Worker does not crash the API process.
- [ ] Re-running a failed/same job is deterministic or safely rejected.

## Suggested implementation order

1. Build a local CLI/script that probes and packages one file.
2. Wrap it in worker/job logic.
3. Store outputs in canonical storage layout.
4. Update DB status and rendition rows.
5. Add thumbnail extraction.
6. Add failure handling.
7. Add smoke test.

## Latest docs to check

- FFmpeg documentation: https://ffmpeg.org/documentation.html
- ffprobe documentation: https://ffmpeg.org/ffprobe.html
- Apple HLS documentation: https://developer.apple.com/documentation/http-live-streaming
- Apple HLS overview: https://developer.apple.com/streaming/

## Required memory entry

Before handoff, write:

```txt
memory/DDMMYY-D-short-topic.md
```

Use `memory/_TEMPLATE.md`. Include changed interfaces, validation, and handoff risks.

## Required grounding

Before implementation, read:

- `docs/00-ground-truth-mvp-spec.md`
- `docs/01-agent-operating-contract.md`
- This sector manifest
- Recent `memory/` entries for this sector and direct dependencies
- Latest official docs for any framework/tool/API touched
