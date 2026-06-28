# Sector F — Authentication and Access Control

Owner: auth/security agent  
Primary mission: make identity, ownership, and private access rules reliable from the start.

## Scope

Build MVP authentication and authorization:

- Clerk integration for user authentication.
- Clerk JWT verification/session handling in frontend and API.
- Current-user endpoint.
- Ownership checks for video CRUD/upload/process/playback.
- Basic privacy model.
- User-safe forbidden/unauthorized error semantics.

## Out of scope

- Enterprise SSO.
- OAuth marketplace integrations.
- Paid subscriber access.
- Age verification.
- Advanced role hierarchy.
- DRM.

## Interfaces consumed

From Sector B:

- User and video ownership schema.
- API route conventions.

From Sector A:

- Auth UI expectations.

## Interfaces provided

To all sectors:

- Current user identity contract.
- Auth middleware/dependency.
- Ownership check helper.
- Unauthorized/forbidden response shape.

To Sector E:

- Playback authorization rules and optional signed URL behavior.

## MVP privacy model

Minimum viable privacy:

```txt
owner-only drafts/uploads/failed videos
ready videos may be public or owner-only depending on product choice
```

If privacy status is implemented, use simple values:

```txt
private, public, unlisted
```

Do not implement paid/subscriber access in MVP.

## Deliverables

- Auth implementation.
- Clerk provider integration.
- Current user endpoint.
- Ownership middleware/helper.
- Tests for user A vs user B access.
- API error response docs.

## Acceptance criteria

- [ ] User can sign in through the local/dev Clerk-backed flow.
- [ ] API can identify current user.
- [ ] User A cannot update/delete/upload to User B's video.
- [ ] User A cannot access private playback for User B's video.
- [ ] Auth errors are consistent and frontend-readable.
- [ ] Secrets are not committed.
- [ ] No custom password storage is introduced unless explicitly approved.
- [ ] Auth design is documented in memory if it affects multiple sectors.

## Suggested implementation order

1. Implement Clerk identity and session/JWT verification.
2. Implement user identity mapping in the API.
3. Add current-user endpoint.
4. Add ownership helpers.
5. Protect video endpoints.
6. Add cross-user tests.
7. Document privacy/playback behavior.

## Latest docs to check

- Clerk docs for the chosen frontend and backend integration path.
- Backend framework security/auth middleware docs.
- OWASP guidance if implementation adds custom auth logic beyond Clerk.

## Required memory entry

Before handoff, write:

```txt
memory/DDMMYY-F-short-topic.md
```

Use `memory/_TEMPLATE.md`. Include changed interfaces, validation, and handoff risks.

## Required grounding

Before implementation, read:

- `docs/00-ground-truth-mvp-spec.md`
- `docs/01-agent-operating-contract.md`
- This sector manifest
- Recent `memory/` entries for this sector and direct dependencies
- Latest official docs for any framework/tool/API touched
