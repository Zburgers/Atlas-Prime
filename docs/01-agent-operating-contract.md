# Agent Operating Contract

Status: required for every implementation agent  
Audience: all sector agents

## 1. Prime directive

Build only the MVP described in `docs/00-ground-truth-mvp-spec.md` unless the human owner explicitly expands scope.

The correct behavior is:

```txt
read spec
  -> inspect repo
  -> check relevant latest official docs
  -> make the smallest useful change
  -> validate
  -> write memory entry
  -> hand off clearly
```

## 2. Required read set before coding

Every agent must read:

1. `docs/00-ground-truth-mvp-spec.md`
2. This file.
3. Its sector manifest in `docs/sectors/`.
4. Any existing `AGENTS.md`, repo instructions, or skill files present in the repository.
5. Recent relevant files in `memory/` for the same sector and direct dependencies.

## 3. Latest-docs rule

When touching a framework/tool/API that may have changed, the agent must check the latest official documentation.

Examples:

- Frontend agents check current framework/player docs.
- API agents check current framework/database migration docs.
- Media agents check FFmpeg/ffprobe docs and verify command behavior locally.
- Delivery agents check static serving/CDN/cache-header docs if adding infrastructure.
- Auth agents check current auth/session/security docs.

Do not rely only on memory or old snippets for framework-specific commands.

## 4. Scope control

Agents must avoid:

- Adding live streaming in the MVP.
- Adding DRM.
- Adding recommendations.
- Adding payments.
- Adding comments/social features.
- Adding mobile apps.
- Replacing the whole stack without owner approval.
- Creating clever distributed architecture before the single-node loop works.

If a feature seems useful but is out of scope, record it as a future note in the handoff, not as implementation work.

## 5. Interface discipline

Cross-sector changes must be explicit.

If a sector changes any of these, it must update dependent docs or write a high-signal memory entry:

- API request/response shape.
- Video status names.
- Database schema.
- Storage key layout.
- HLS output layout.
- Auth/session behavior.
- Worker job payload.
- Environment variables.
- Local startup commands.

## 6. Minimal changelog / ADR requirement

Every handoff must add one file under `memory/`.

Filename:

```txt
memory/DDMMYY-SECTOR-short-topic.md
```

Example:

```txt
memory/280626-C-resumable-upload-contract.md
```

Use the template in `memory/_TEMPLATE.md`.

A good memory entry is short, factual, and useful to the next agent. It should answer:

- What changed?
- Why was that decision made?
- What did you validate?
- What should the next agent know?

## 7. Validation rule

Every sector should leave behind at least one repeatable validation method.

Acceptable validation types:

- Unit test.
- Integration test.
- Smoke command.
- Manual browser check with exact steps.
- FFmpeg/ffprobe command output summary.
- API request example.

If validation cannot be run, the agent must write why.

## 8. Error-handling rule

Do not hide failures.

A good implementation exposes:

- User-safe failure message.
- Developer-facing logs.
- Durable failed state in DB when relevant.
- Retry path if appropriate.

## 9. Commit/work unit guidance

Each agent should prefer small, reviewable work units.

Good examples:

- Add video status schema and migration.
- Add upload endpoint and storage service.
- Add worker command that generates HLS for one file.
- Add watch page that plays existing HLS URL.

Bad examples:

- Rebuild the entire platform in one diff.
- Change stack choices without recording why.
- Mix UI redesign, database migration, and worker rewrite in one handoff.

## 10. Handoff checklist

Before declaring a sector task done:

- [ ] Main spec still matches implementation.
- [ ] Sector acceptance criteria are satisfied or clearly marked incomplete.
- [ ] Tests/smoke checks run or documented as not run.
- [ ] `memory/` entry added.
- [ ] New environment variables documented.
- [ ] Cross-sector interface changes documented.
- [ ] Known risks are written down.
