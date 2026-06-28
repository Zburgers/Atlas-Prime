# Sector H — Testing, DevEx, and CI

Owner: devex/testing agent  
Primary mission: make the project easy to run, test, and verify repeatedly.

## Scope

Build the local engineering foundation:

- Repo structure recommendation.
- Docker Compose for web/api/database/queue/worker/MinIO where applicable.
- `.env.example`.
- Makefile or task runner.
- Test commands.
- Sample media fixture strategy.
- CI checks.
- Smoke test for upload -> process -> playback metadata.

## Out of scope

- Kubernetes.
- Production autoscaling.
- Full performance/load testing.
- Cloud deployment automation.

## Interfaces consumed/provided

This sector supports all others.

It should provide:

- Standard local startup command.
- Standard test command.
- Standard lint/format command if used.
- Standard migration command.
- Standard smoke command.
- Fixture storage location.
- Documented env contract for Clerk, PostgreSQL, Redis, and MinIO.

## Suggested repo shape

If starting from scratch, prefer a monorepo shape like:

```txt
apps/
  web/
  api/
workers/
  media/
packages/
  shared/
docs/
  sectors/
memory/
fixtures/
  media/
infra/
  docker/
```

This is a recommendation, not a hard requirement. If the repo is already structured differently, adapt rather than rewrite unnecessarily.

## Deliverables

- Local setup docs.
- `.env.example`.
- Docker Compose or equivalent local orchestration.
- Test runner setup.
- Sample video fixture or documented fixture generation command.
- Smoke test script skeleton.
- CI workflow skeleton.

## Acceptance criteria

- [ ] New developer can start the stack from documented commands.
- [ ] DB and queue run locally.
- [ ] MinIO runs locally with documented buckets or bootstrap steps.
- [ ] Worker can be started locally.
- [ ] Tests can be run with one documented command.
- [ ] Smoke test path is documented even if initially partial.
- [ ] Sample media fixture is small and legal to keep/use.
- [ ] CI does not require local secrets.
- [ ] Environment variables are documented.

## Suggested implementation order

1. Inspect repo and choose minimal local orchestration.
2. Add `.env.example`.
3. Add task runner/Makefile commands.
4. Add database/queue/object-storage services.
5. Add worker startup path.
6. Add sample fixture strategy.
7. Add CI checks.
8. Add smoke test.

## Latest docs to check

- Docker Compose docs.
- Chosen test framework docs.
- Chosen CI provider docs.
- FFmpeg install/runtime docs if worker is containerized.

## Required memory entry

Before handoff, write:

```txt
memory/DDMMYY-H-short-topic.md
```

Use `memory/_TEMPLATE.md`. Include changed interfaces, validation, and handoff risks.

## Required grounding

Before implementation, read:

- `docs/00-ground-truth-mvp-spec.md`
- `docs/01-agent-operating-contract.md`
- This sector manifest
- Recent `memory/` entries for this sector and direct dependencies
- Latest official docs for any framework/tool/API touched
