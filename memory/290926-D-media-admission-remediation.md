# 290926-D-media-admission-remediation

Sector: D — Media Processing and HLS Packaging
Agent: Codex / GPT-6 Luna
Date: 29-09-2026
Branch/Commit: `codex/plan6-6-media-admission`, based on `63c0d1bc89fac874821abe07aec0d950562d7289` (uncommitted)

## What changed
- Normalize ffprobe duration, rational rates, encoded/effective dimensions, and display-matrix rotation; reject metadata outside the approved D-014 envelope before packaging/thumbnail FFmpeg.
- Persist sanitized `MEDIA_POLICY_REJECTED` categories through the existing generation-fenced failure path.
- Strictly validate admission/timeout configuration; set FFmpeg timeout default to 1,800 seconds. R-001 is unchanged; no CPU or memory caps added.

## Decisions / ADR notes
- Decision: apply the owner-approved `docs/decisions/D-014-decoded-media-envelope.md` as the exact policy source; environment overrides may tighten limits only.
- Reason: enforce the approved single-node decoded-work bounds without using upload bytes or post-start timeout as admission controls.
- Alternatives considered: none.

## Validation
- Focused worker tests: `docker compose -f compose.yaml --project-directory <worktree> run --rm --build worker pytest tests/test_packager.py tests/test_repository.py -q` — 52 passed.
- `make worker-test` — 52 passed, including real fixture packaging and zero FFmpeg subprocess launches on policy rejection.
- `make lint` — Compose config, API/worker compileall, web build and lint passed.
- `ruff check` on touched worker source/tests and `git diff --check` — passed.

## Files touched
- `workers/media/media_worker/{packager,config,celery_app}.py`
- `workers/media/tests/{test_packager,test_repository}.py`
- `.env.example`, `compose.yaml`, `docs/sectors/D-media-processing-packaging.md`
- `memory/290926-D-media-admission-remediation.md`

## Handoff / risks
- The 12-second research fixture does not prove 10-minute throughput; no CPU/memory caps were inferred from it.
- The supplied D-014 file was already untracked and remains untouched; retain it as owner-provided decision evidence.
- Changes are uncommitted on the requested branch; no push or PR was created.
