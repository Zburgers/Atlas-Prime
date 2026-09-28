# D-014 — Decoded-media admission envelope

Status: **APPROVED BY OWNER-DELEGATED DECISION — 2026-09-29**

The owner delegated product and technical decisions for the self-hosted YouTube-style MVP to the implementation agent on 2026-09-29. This record selects the initial single-node admission envelope; it does not change R-001 upload-byte policy.

## Approved limits

- Maximum duration: 600 seconds.
- Maximum effective width and height: 1920 × 1920 pixels.
- Maximum effective pixel area: 2,073,600 pixels.
- Maximum frame rate: 30 fps.
- Maximum decoded work: 37,324,800,000 pixel-frames (`effective_pixel_area × selected_fps × duration`).
- Keep media-worker task concurrency at its existing single-worker setting. Do not add Compose CPU or memory caps from host-only child-RSS measurements.
- Set the per-FFmpeg-process timeout default to 1,800 seconds. This is an execution guard, not an admission substitute or throughput guarantee.
- R-001 upload-byte limit: unchanged.

The 10-minute duration is deliberately conservative for this single-node MVP. The bounded spike measured only up to 12 seconds of packaging; it does not establish 10-minute throughput or container resource use. Reconsider the duration and any container resource caps only after a representative isolated-worker benchmark.

## Metadata rules

- Duration: parse finite positive stream and container durations. If both are valid, use the longer. If only one is valid, use it. Reject when neither is valid.
- Frame rate: parse `avg_frame_rate` and `r_frame_rate` as exact positive rationals. If both are valid, use the higher; if one is valid, use it; reject if neither is valid. This intentionally favors false rejection over a low-rate-field bypass.
- Rotation: absent display-matrix rotation means 0°. Normalize signed degrees modulo 360; accept only 0°, 90°, 180°, or 270°. Reject malformed, non-finite, or non-right-angle values. Swap effective width/height for 90° and 270°.
- Dimensions: reject missing, malformed, zero, or negative encoded dimensions. Apply width, height, and pixel-area limits to effective display dimensions.
- Work: calculate with exact arithmetic; reject when the decoded-work product exceeds the approved cap.
- Do not coerce `N/A`, malformed rationals, zero denominators, or non-finite values into permissive defaults.

## Evidence and tradeoff

See `docs/research/2026-09-08-media-complexity-admission-spike.md`. The short 1080p30 sample packaged in 3.791 seconds with 389.3 MiB peak child RSS; the half-second 4K60 sample peaked at 495.4 MiB. Those measurements justify bounding decoded geometry and frame rate, but not extrapolating long-duration throughput. A 10-minute ceiling supports useful long-form MVP uploads while containing work well below the report's 30-minute balanced proposal. It excludes 4K and >30 fps input for now.

Strongest rejected alternative: the 30-minute balanced proposal. Its arithmetic cap is 111,974,400,000 pixel-frames, but the research contains no long-duration measurement to support accepting that much work on the single-node target.
