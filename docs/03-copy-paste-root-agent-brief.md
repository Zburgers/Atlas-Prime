# Root Agent Brief — Optional Copy Into `AGENTS.md`

This file can be copied into a root `AGENTS.md` or merged into existing repo instructions.

## Required behavior

Before editing code:

1. Read `docs/00-ground-truth-mvp-spec.md`.
2. Read `docs/01-agent-operating-contract.md`.
3. Read your sector manifest in `docs/sectors/`.
4. Inspect recent relevant files in `memory/`.
5. Check latest official docs for the tool/framework you are modifying.
6. Keep changes inside MVP scope.
7. Validate your work.
8. Add a short memory entry under `memory/DDMMYY-SECTOR-short-topic.md`.

## MVP scope reminder

Build VOD-first upload -> process -> HLS playback.

Do not add live streaming, DRM, recommendations, payments, mobile apps, Kubernetes, or distributed transcoding before the first complete local VOD loop works.

## Memory entry required

Use `memory/_TEMPLATE.md` for every handoff.
