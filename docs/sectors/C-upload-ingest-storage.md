# Sector C — Upload, Ingest, and Storage

Owner: upload/storage agent  
Primary mission: get original media safely from the user's browser into controlled storage.

## Scope

Build the upload path:

- Upload endpoint or signed-upload flow into MinIO.
- File size limits.
- Media type validation.
- Original media storage layout.
- Upload completion handling.
- Storage service abstraction.
- Job enqueue trigger after successful upload.

## Out of scope

- Actual transcoding.
- HLS playback.
- CDN optimization.
- Full malware scanning service unless trivial/local.
- Resumable multipart upload unless explicitly chosen for MVP.

## Interfaces consumed

From Sector B:

- Video model.
- Status transitions.
- Original storage key field.
- Processing job creation model.

From Sector F:

- Authenticated user identity.
- Ownership checks.

From Sector H:

- Local service/bootstrap conventions and dev/test fixtures.

## Interfaces provided

To Sector D:

- Stable original media storage key.
- Metadata about uploaded file.
- Processing job payload shape.

To Sector A:

- Upload API response and failure states.

To Sector G:

- Upload errors and storage logs.

## Storage layout

Canonical object storage key layout:

```txt
originals/{video_id}/source.{ext}
processed/{video_id}/hls/master.m3u8
```

Use MinIO as the MVP storage backend from day one. Do not expose bucket internals or raw absolute filesystem paths through public API responses.

## Deliverables

- S3-compatible storage service abstraction.
- Upload endpoint or direct-upload orchestration.
- File validation logic.
- Controlled filename/path generation.
- Status update to `uploaded` after successful storage.
- Enqueue processing job or call Sector B job service.
- Tests for invalid file, unauthorized upload, and successful upload.

## Acceptance criteria

- [ ] User can upload a small MP4 through API.
- [ ] Upload is associated with a video owned by that user.
- [ ] Upload cannot write outside controlled storage paths.
- [ ] Invalid file type/oversized file is rejected cleanly.
- [ ] Successful upload updates video status to `uploaded` or `queued` depending on enqueue timing.
- [ ] Processing job is created after successful upload if queue exists.
- [ ] API response does not leak host absolute paths.
- [ ] Upload failure produces visible status/logs.

## Suggested implementation order

1. Define storage service interface.
2. Implement MinIO/S3-compatible storage.
3. Add upload endpoint and validation.
4. Wire status transition.
5. Wire job enqueue.
6. Add tests.
7. Document upload flow and storage-key contract for downstream sectors.

## Latest docs to check

- Backend framework file upload docs.
- Object storage SDK docs for the chosen MinIO/S3-compatible client.
- Celery docs if enqueue behavior is implemented here.

## Required memory entry

Before handoff, write:

```txt
memory/DDMMYY-C-short-topic.md
```

Use `memory/_TEMPLATE.md`. Include changed interfaces, validation, and handoff risks.

## Required grounding

Before implementation, read:

- `docs/00-ground-truth-mvp-spec.md`
- `docs/01-agent-operating-contract.md`
- This sector manifest
- Recent `memory/` entries for this sector and direct dependencies
- Latest official docs for any framework/tool/API touched
