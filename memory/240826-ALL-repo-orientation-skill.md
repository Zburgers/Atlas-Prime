# 240826-ALL-repo-orientation-skill

Sector: A-H / repository orientation
Agent: Codex
Date: 24-08-2026
Branch/Commit: docs/fullplatform-rollout / 6ee3323 before this handoff

## What changed
- Added `skills/atlasprime-repo-orientation/SKILL.md` and its `references/system-map.md` with the current Compose services, API/web entry points, background jobs, domain systems, contracts, and safe validation commands.
- Added the required orientation-skill reference to `AGENTS.md`.

## Decisions / ADR notes
- Decision: keep the skill entrypoint short and place the detailed service map in a linked reference.
- Reason: fresh agents can load the routing instructions quickly while selectively using the larger map for the system they will touch.
- Alternatives considered: a second README or a global skill; rejected because the owner requested a repo-local skill that every fresh agent can find through `AGENTS.md`.

## Validation
- `python /home/naki/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/atlasprime-repo-orientation` — PASS (`Skill is valid!`).
- Required reference existence, trailing-whitespace, and `git diff --check -- AGENTS.md` checks — PASS.
- `docker compose config -q` — PASS.
- Application test suite — not run; implementation work is active in this checkout and the telemetry-related dirty/untracked files were preserved.

## Files touched
- `skills/atlasprime-repo-orientation/SKILL.md`
- `skills/atlasprime-repo-orientation/references/system-map.md`
- `AGENTS.md`

## Handoff / risks
- The map was inspected at branch `docs/fullplatform-rollout`, commit `6ee3323`; recheck current code and worktree before relying on snapshot details.
- `apps/api/app/services/telemetry_metrics.py` was untracked at inspection time and additional telemetry files were dirty by validation; all such work was intentionally excluded from this commit. Do not clean, overwrite, or silently absorb it into unrelated work.
- The skill documents local/CI evidence boundaries and does not claim deployment, authenticated browser qualification, or production readiness.
