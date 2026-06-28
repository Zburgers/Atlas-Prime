# Memory Folder — Minimal Changelog / ADR Log

This folder is the project handoff memory.

Every sector agent must add a short markdown entry here before handoff.

## Filename format

```txt
DDMMYY-SECTOR-short-topic.md
```

Examples:

```txt
280626-A-upload-status-ui.md
280626-B-video-status-schema.md
280626-D-hls-worker.md
```

## Purpose

These files should make the project easy to resume and audit.

They should capture:

- What changed.
- Why important decisions were made.
- What was validated.
- What the next agent/human owner needs to know.

## Rules

- Keep entries minimal and searchable.
- Do not write long essays.
- Do not overwrite another entry.
- Use `memory/_TEMPLATE.md`.
- Write `Not run` under validation if validation was not run.
- Record cross-sector interface changes clearly.
