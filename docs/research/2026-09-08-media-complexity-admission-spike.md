# Research Protocol — #19 Decoded-Media Admission Envelope

Status: **BOUNDED SPIKE REQUIRED**
Parent: `docs/plans/2026-09-08-06-post-merge-stabilization.md`, task 6.2
Planned against: `main` at `50e3f325c5e07376c4b703312d3f422d7ecd572c`
Issue: #19
Date: 2026-09-08

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

- [ ] current code seam and pre-FFmpeg insertion point confirmed;
- [ ] no more than the bounded experiment matrix executed;
- [ ] rotation and fractional/malformed fps behavior demonstrated;
- [ ] timing/peak-memory evidence table present;
- [ ] 2–3 candidate envelopes present with tradeoffs;
- [ ] strongest rejected candidate stated;
- [ ] D-014 proposal is explicit and still marked `NEEDS OWNER APPROVAL`;
- [ ] R-001 is not silently changed;
- [ ] no production admission code changed;
- [ ] research PR is based on fresh `main` and records its exact SHA.

## Stop conditions

Stop the spike and report instead of expanding scope if:

- the probe result cannot reliably expose a policy-critical field;
- current FFmpeg/ffprobe build behavior contradicts this protocol;
- the worker/container environment cannot produce meaningful measurements;
- a safe limit would require a new product requirement (e.g. mandatory 4K support);
- the research uncovers a distinct P1/P0 parser or command-injection defect.

A stop is a valid research outcome. Do not convert uncertainty into arbitrary numbers.
