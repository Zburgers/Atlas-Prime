# Research Protocol — #19 Decoded-Media Admission Envelope

Status: **RESEARCH COMPLETE — NEEDS OWNER APPROVAL**
Parent: `docs/plans/2026-09-08-06-post-merge-stabilization.md`, task 6.2
Research checkout: fresh `origin/main` at `63c0d1bc89fac874821abe07aec0d950562d7289`
Issue: #19
Research date: 2026-09-29

## Purpose

Atlas Prime currently limits compressed upload bytes but does not have an owner-approved limit for decoded media complexity. A small compressed source can still represent a long-duration, high-resolution, or high-frame-rate decode/transcode workload.

This spike exists **only** to produce enough measured evidence for a numeric owner decision. It is not authorization to implement limits.

## Known repository facts

At the planning base:

- API upload bytes are controlled by `ATLAS_UPLOAD_MAX_BYTES` (local default 100 MiB), but R-001 says the maximum upload-size decision remains open.
- the worker uses one `ffprobe` pass before packaging;
- the current `MediaProbe` records duration, width, height, codecs, bitrate and audio presence;
- frame rate and display rotation/effective dimensions are not normalized into the worker policy surface;
- `ATLAS_FFMPEG_TIMEOUT_SECONDS` bounds process wall time only after FFmpeg starts; it is not an admission policy;
- the Compose media worker runs with concurrency 1 and has no explicit CPU/memory resource limit in the current local stack.

## Decision needed

Create owner decision **D-014 — decoded-media processing envelope**.

D-014 must explicitly decide:

1. maximum duration in seconds;
2. maximum effective display width and height and/or pixel area;
3. maximum frame rate;
4. whether an additional derived decoded-work ceiling is required (for example effective pixels × fps × duration) or whether independent limits are sufficient for MVP;
5. how to treat:
   - missing duration;
   - non-finite duration/rate;
   - zero/negative dimensions/rate;
   - rotation metadata;
   - conflicting `avg_frame_rate` and `r_frame_rate`;
6. whether local Compose worker CPU/memory caps are required in the same remediation;
7. confirmation that R-001 upload-byte limit is unchanged, or a separate explicit R-001 decision if the owner wants to change it.

## Hard bounds on the spike

The spike must finish in one research PR and may not:

- change production worker admission behavior;
- add a permanent large media fixture;
- run an unbounded resolution × duration × fps matrix;
- benchmark cloud/CDN/production infrastructure;
- redesign the encoding ladder;
- decide #14–#17;
- substitute internet-provider limits for Atlas Prime owner policy.

Target: **no more than six generated probe/transcode cases** plus up to two metadata-only parser fixtures.

## Experiment matrix

Use generated, legal FFmpeg test sources. Do not commit the generated media unless an individual fixture remains small enough for the existing fixture policy.

Minimum cases:

| Case | Purpose | Suggested shape |
|---|---|---|
| A | current healthy baseline | existing small fixture |
| B | HD baseline | short 1920×1080 @ 30fps |
| C | frame-rate pressure | short 1920×1080 @ 60fps |
| D | resolution pressure | very short 3840×2160 @ 30fps |
| E | combined pressure | very short 3840×2160 @ 60fps |
| F | long-duration characteristic without a huge committed file | generated low-complexity source long enough to measure scaling, or measure a bounded shorter source and clearly label extrapolation rather than pretending it is measured |

Also create/provide ffprobe JSON fixtures for:

- 90°/270° display rotation;
- fractional frame rate such as 30000/1001, and a missing/zero-rate edge case.

If the local machine cannot practically encode a case, record that as evidence; do not expand the benchmark until it eventually succeeds.

## Exact measurements

For each executed case record:

- generated source command;
- source size;
- ffprobe wall time;
- normalized duration;
- encoded width × height;
- display rotation/effective width × height;
- `avg_frame_rate`;
- `r_frame_rate`;
- selected normalized fps and why;
- package/transcode wall time;
- peak resident memory for the worker/FFmpeg process if available;
- outcome/timeout;
- local CPU model/core count and available memory at a coarse level (no personal identifiers).

Prefer repeatable commands such as:

```sh
/usr/bin/time -v ffprobe ...
/usr/bin/time -v ffmpeg ...
docker compose run --rm worker ...
```

If `/usr/bin/time -v` is unavailable in the worker image, measure from the host or use a documented equivalent. Do not silently mix incomparable measurement methods.

## ffprobe parser research

Use structured JSON and select only fields needed by policy. Verify current official ffprobe behavior for:

- stream width/height;
- `avg_frame_rate` and `r_frame_rate`;
- format/stream duration fallback;
- side-data/display-matrix rotation.

The resulting implementation proposal must define deterministic precedence. A policy check must never treat malformed rational strings, `N/A`, zero denominators, NaN, or infinity as a harmless zero.

Official starting point: https://ffmpeg.org/ffprobe.html

## Candidate policy output

The research PR must present **2–3 candidate envelopes**, not one disguised decision.

Use this table:

| Candidate | Max duration | Max effective geometry | Max fps | Derived work cap | Compose resource cap | Why choose it | What it rejects |
|---|---:|---|---:|---|---|---|---|
| Conservative | TBD from evidence | TBD | TBD | TBD | TBD | ... | ... |
| Balanced | TBD from evidence | TBD | TBD | TBD | TBD | ... | ... |
| Permissive learning | TBD from evidence | TBD | TBD | TBD | TBD | ... | ... |

Numeric values must be justified by the measured matrix and the product's single-node learning-MVP goal. They must not be copied from YouTube/Vimeo/etc. as authority.

## Recommended decision shape

After measurements, append:

```md
## Proposed D-014

Status: NEEDS OWNER APPROVAL

- max_duration_seconds: <number>
- max_effective_width: <number>
- max_effective_height: <number>
- max_frame_rate: <number>
- decoded_work_cap: <number or none>
- missing_or_nonfinite_metadata: reject | defined fallback
- rotation_policy: <explicit>
- frame_rate_precedence: <explicit>
- compose_worker_cpu_limit: <value or deferred>
- compose_worker_memory_limit: <value or deferred>
- R-001 upload bytes: unchanged | separately changed by owner

Evidence:
- <table/commands>

Strongest rejected alternative:
- <candidate and reason>
```

The owner must explicitly approve D-014 before Plan 6 task 6.6 begins.

## Research acceptance criteria

- [x] current code seam and pre-FFmpeg insertion point confirmed;
- [x] six-case bounded experiment matrix executed; no case was impractical;
- [x] rotation and fractional/malformed fps behavior demonstrated;
- [x] timing/peak-memory evidence table present;
- [x] 2–3 candidate envelopes present with tradeoffs;
- [x] strongest rejected candidate stated;
- [x] D-014 proposal is explicit and still marked `NEEDS OWNER APPROVAL`;
- [x] R-001 is not silently changed;
- [x] no production admission code changed;
- [x] local research artifact is based on fresh `main` and records its exact SHA; no PR was opened per task scope.

## Stop conditions

Stop the spike and report instead of expanding scope if:

- the probe result cannot reliably expose a policy-critical field;
- current FFmpeg/ffprobe build behavior contradicts this protocol;
- the worker/container environment cannot produce meaningful measurements;
- a safe limit would require a new product requirement (e.g. mandatory 4K support);
- the research uncovers a distinct P1/P0 parser or command-injection defect.

A stop is a valid research outcome. Do not convert uncertainty into arbitrary numbers.

---

## Research results (2026-09-29)

### Checkout and current worker path

- Exact base: `63c0d1bc89fac874821abe07aec0d950562d7289` (`origin/main`).
- The upload byte limit remains `ATLAS_UPLOAD_MAX_BYTES`; this spike does not change R-001 or the limit.
- `workers/media/media_worker/celery_app.py::process_video` downloads the original, calls `probe_media(source_path)`, logs the returned metadata, calls `repository.mark_processing(...)`, and then calls `package_to_hls(...)`.
- `workers/media/media_worker/packager.py::probe_media` invokes one `ffprobe -v error -print_format json -show_format -show_streams` subprocess with a 30-second timeout. It reads first-video-stream width/height, stream-duration then container-duration fallback, codecs, and bitrate. It does not read frame rates or `side_data_list`; `MediaProbe` has no fps or rotation fields.
- The policy insertion point, if approved later, is immediately after `probe_media` and before `mark_processing`/`package_to_hls`; this is before packaging's first rendition or thumbnail FFmpeg command. No code was changed here.
- `package_to_hls` encodes every eligible rung in the 1080p/720p/480p/360p ladder sequentially and then runs one to three thumbnail FFmpeg processes. The worker's ordinary FFmpeg timeout does not limit decoded work before or during the probe.

### Machine, tools, and method

- Host: Linux x86_64, Intel Core i5-7600T, 4 online cores; 31 GiB RAM, approximately 14 GiB available before the run. No personal machine identifiers are included.
- Host tools: `ffmpeg version 8.1.2`, `ffprobe version 8.1.2`; `/usr/bin/time` is absent.
- Measurement used Python 3 standard-library `subprocess`, `time.monotonic`, and `resource.getrusage(RUSAGE_CHILDREN)`. Probe/package wall time is elapsed time around the subprocess group; child CPU is summed user+system CPU for its children; peak RSS is the largest single ffprobe/FFmpeg child, not the Python worker plus child or a sum of processes. One fresh measurement wrapper was used per case. All processes exited 0; no timeout.
- These are host measurements, not measurements inside the Debian `python:3.12-slim` worker image or Compose cgroups. No Docker Compose services were started. Host FFmpeg build, CPU scheduling, and resource limits can differ from the worker deployment.
- Generated sources and HLS output were temporary under `/tmp`; none are committed. The six matrix rows are the only probe/package cases. Rotation remuxes and the fractional-rate source below are metadata-only checks, not additional package cases.

Generation commands (shared options shown exactly; replace placeholders with table values):

```sh
ffmpeg -y -hide_banner -loglevel error \
  -f lavfi -i 'testsrc2=size=WIDTHxHEIGHT:rate=FPS:duration=SECONDS' \
  -an -c:v libx264 -preset ultrafast -threads 1 -pix_fmt yuv420p \
  -movflags +faststart CASE.mp4
```

Case A additionally used `-f lavfi -i 'testsrc=size=640x360:rate=24' -f lavfi -i 'sine=frequency=1000:sample_rate=48000' -t 2`, encoded video with libx264/ultrafast/one thread/yuv420p and audio AAC at 96 kbit/s. This matches the dimensions, two-second duration, and audio shape used by `workers/media/tests/test_packager.py`'s generated fallback fixture; that test fixture is not checked in as a media file.

Probe command for every case:

```sh
ffprobe -v error -print_format json -show_format -show_streams CASE.mp4
```

Packaging measurements mirrored the checked-in `package_to_hls` rendition selection, filters, codecs, HLS flags, and thumbnail offsets in `packager.py`, with its four possible rungs, sequentially. Case A/F selected only 360p; B–E selected all four rungs. Package wall/CPU/RSS cover all rendition and thumbnail subprocesses, but exclude fixture generation and the separate ffprobe measurement.

### Bounded matrix

Pixel-frames are `encoded width × encoded height × normalized avg_frame_rate × duration`; they are workload descriptors, not a proven cost model.

| Case | Generated source / purpose | Source bytes | ffprobe wall / CPU / peak RSS | Probe excerpt (width×height; duration; avg / r fps) | Pixel-frames | Package wall / child CPU / peak child RSS | FFmpeg calls |
|---|---|---:|---|---|---:|---|---:|
| A | 640×360 @ 24, 2 s + AAC; healthy baseline | 73,403 | 0.192 s / 0.188 s / 72.3 MiB | 640×360; 2.000 s; 24/1 / 24/1 | 11.1 M | 1.022 s / 1.061 s / 117.7 MiB | 4 |
| B | 1920×1080 @ 30, 2 s; HD baseline | 3,863,369 | 0.205 s / 0.198 s / 71.9 MiB | 1920×1080; 2.000 s; 30/1 / 30/1 | 124.4 M | 3.791 s / 7.072 s / 389.3 MiB | 7 |
| C | 1920×1080 @ 60, 1 s; fps pressure | 3,486,539 | 0.181 s / 0.179 s / 71.6 MiB | 1920×1080; 1.000 s; 60/1 / 60/1 | 124.4 M | 3.445 s / 6.379 s / 390.4 MiB | 5 |
| D | 3840×2160 @ 30, 0.5 s; resolution pressure | 3,874,734 | 0.198 s / 0.194 s / 84.7 MiB | 3840×2160; 0.500 s; 30/1 / 30/1 | 124.4 M | 2.525 s / 4.391 s / 450.8 MiB | 5 |
| E | 3840×2160 @ 60, 0.5 s; combined pressure | 6,819,658 | 0.210 s / 0.207 s / 84.7 MiB | 3840×2160; 0.500 s; 60/1 / 60/1 | 248.8 M | 3.326 s / 6.880 s / 495.4 MiB | 5 |
| F | 640×360 @ 30, 12 s; bounded duration sample | 2,912,649 | 0.210 s / 0.193 s / 71.7 MiB | 640×360; 12.000 s; 30/1 / 30/1 | 82.9 M | 1.541 s / 2.460 s / 115.8 MiB | 4 |

F is a 12-second sample, not a long-duration measurement; it cannot justify linear extrapolation to minutes or hours. B–E also show that equal pixel-frame counts do not imply equal wall time or memory: the input resolution, scaling/rendition ladder, encoder behavior, and host state matter. Peak memory is a single child peak, not a Compose/container limit.

### ffprobe behavior and JSON evidence

The official [ffprobe documentation](https://ffmpeg.org/ffprobe.html) specifies JSON output (`-of json` / `-print_format json`), `-show_streams`, `-show_format`, and `-show_entries`; it describes the selected report sections but does not define a policy for normalizing these fields. The installed FFmpeg 8.1.2 behavior was therefore checked locally.

For a real 90° display-matrix sample, made by remuxing B with `ffmpeg -display_rotation:v:0 90 -i B.mp4 -c copy rot90.mp4`, the relevant ffprobe JSON was:

```json
{"streams":[{"width":1920,"height":1080,"avg_frame_rate":"30/1","r_frame_rate":"30/1","duration":"2.000000","side_data_list":[{"side_data_type":"Display Matrix","rotation":90}]}],"format":{"duration":"2.000000"}}
```

The 270° remux emitted `rotation: -90` with the same encoded dimensions and rates. Normalize angle modulo 360; both 90 and -90/270 swap effective width and height. The legacy `-metadata:s:v:0 rotate=90` remux emitted no display matrix in this build and is not a reliable fixture-generation command. The input `-display_rotation` option was required.

A separate short generated source at 30000/1001 emitted:

```json
{"streams":[{"width":640,"height":360,"r_frame_rate":"30000/1001","avg_frame_rate":"30000/1001","duration":"1.001000"}],"format":{"duration":"1.001000"}}
```

The combined metadata-only malformed/missing-field parser fixture proposed for future policy tests is synthetic (not output from a valid encoded source):

```json
{"streams":[{"codec_type":"video","width":640,"height":360,"avg_frame_rate":"N/A","r_frame_rate":"0/0","duration":"N/A","side_data_list":[]}],"format":{"duration":"N/A"}}
```

Do not coerce malformed fractions, `N/A`, zero denominators, zero/negative dimensions, or non-finite values to zero. JSON itself has no standard NaN/Infinity numbers; parser tests should cover string spellings and invalid numeric values at the parser boundary.

### Candidate envelopes for owner discussion

The work caps below are arithmetic products of each candidate's maximum area × maximum fps × maximum duration. They are not measured maximums and must not be described as safe CPU budgets. All candidate limits are policy choices; the short matrix only confirms parser fields and gives a small local cost comparison.

| Candidate | Max duration | Max effective geometry | Max fps | Derived work cap | Compose resource cap | Why choose it | What it rejects |
|---|---:|---|---:|---:|---|---|---|
| Conservative | 600 s | long edge ≤1280; area ≤921,600 px | 30 | 16,588,800,000 px-frames | Defer pending target Compose/container measurement | Lowest decoded work, close to the existing lower-rung learning profile | 1080p/4K, >30 fps, >10 min |
| Balanced (proposed) | 1800 s | long edge ≤1920; area ≤2,073,600 px | 30 | 111,974,400,000 px-frames | Defer pending target Compose/container measurement | Allows 1080p learning-MVP uploads; B measured 2 s at 3.791 s package wall and 389.3 MiB peak child RSS | 4K, >30 fps, >30 min |
| Permissive learning | 3600 s | long edge ≤3840; area ≤8,294,400 px | 60 | 1,791,590,400,000 px-frames | Defer pending target Compose/container measurement | Allows case E's 4K60 shape under independent duration/work caps; no long-duration cost is validated | >4K, >60 fps, >60 min |

The maximum work products are respectively about 67×, 450×, and 7,200× case E's 248.8 million pixel-frames. This is arithmetic only; no duration-scale throughput or memory extrapolation is validated. In particular, the balanced candidate's 30-minute limit is not established by case F. The owner should reduce duration or require a longer isolated benchmark before relying on the proposed value.

### Proposed D-014

Status: **NEEDS OWNER APPROVAL**

- `max_duration_seconds`: 1800 (balanced candidate; owner must decide whether the unmeasured 30-minute duration is acceptable).
- `max_effective_width`: 1920 and `max_effective_height`: 1920, with `max_effective_pixel_area`: 2,073,600 (orientation-independent 1080p envelope; both dimensions still must be positive).
- `max_frame_rate`: 30 fps.
- `decoded_work_cap`: 111,974,400,000 pixel-frames (`effective_pixel_area × selected_fps × duration`); the independent dimension/rate/time ceilings still apply.
- `missing_or_nonfinite_metadata`: reject if no valid positive finite value is available after the explicit duration fallback; reject if neither frame-rate field parses as a positive finite rational; reject nonpositive dimensions and malformed rotation.
- `rotation_policy`: no display-matrix side data means 0°; accept right-angle multiples only; normalize signed degrees modulo 360 and swap effective dimensions for 90°/270°. Owner must decide treatment of non-right-angle transforms.
- `frame_rate_precedence`: parse both `avg_frame_rate` and `r_frame_rate` as exact rationals; if both are valid and disagree, use the higher value for admission; use the sole valid positive value if only one is available; reject if neither is valid. This avoids a low-field bypass but may reject variable-frame-rate inputs whose nominal rate greatly exceeds the average.
- `duration_precedence`: use positive finite stream duration; if absent/invalid, use positive finite format duration. If both valid but conflict, proposed conservative rule is the larger value; owner must approve this false-rejection tradeoff.
- `compose_worker_cpu_limit`: deferred; this host-only run did not measure an isolated worker container or test a CPU quota.
- `compose_worker_memory_limit`: deferred; child RSS is not container peak/limit evidence.
- `R-001 upload bytes`: unchanged by this research; no upload-byte decision is made here.

Evidence: cases A–F and ffprobe excerpts above. The spike did not establish a safe long-duration CPU/memory envelope or Compose resource limit.

Strongest rejected alternative: no decoded-media admission limits, relying on compressed upload bytes and the FFmpeg timeout. The 4K60 case is only 6.82 MB compressed yet reaches 495.4 MiB peak FFmpeg-child RSS during a half-second package. The timeout does not constrain decoded dimensions/rate and cannot prevent resource use before it fires.

### Owner ambiguity / handoff

**NEEDS OWNER DECISION: D-014.** The balanced candidate is a proposal, not an approved limit. The owner must decide whether 30 minutes at 1080p30 and its arithmetic work cap are acceptable for the single-node learning MVP, whether to first measure a longer isolated-worker fixture, how to treat conflicting duration/rate metadata and arbitrary-angle rotation, and whether Compose CPU/memory caps belong in the same remediation. R-001 upload bytes remain unchanged and separate.
