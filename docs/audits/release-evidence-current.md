# Release Evidence: PR #12 Merge-Readiness Candidate

Status: implementation/test reconciliation is complete; the docs-inclusive final head still requires exact-head CI before merge. Deployment, authenticated browser qualification, and production remain unverified.

## Candidate

- Branch: `docs/fullplatform-rollout`
- Current implementation/test candidate SHA: `c5140fc4fe05314dfa29116891831c85802e7341`
- Final telemetry runtime change: `903a3b1080b661a3ca96c6b24d5f98f6fa48ee52`
- Pull request: [#12](https://github.com/Zburgers/Atlas-Prime/pull/12)
- Main base: `8d0ebc5f7c08d66c2d5edbe910c1aee740bed9b3`
- Superseded telemetry candidate: `266b4600a3973753357a46800c96460aae2cbcfc` (CI run `34201068181`).

## Implementation Candidate vs Docs-Inclusive Head

- `903a3b1` is the last runtime-behavior commit. It restores the approved D-013 per-client telemetry semantics while keeping cookie/session rotation bounded.
- `c5140fc` adds focused policy regressions proving two legitimate anonymous clients on the same video each retain an independent 120-event/minute budget while fresh-identity rotation remains bounded.
- Later commits on this branch are documentation/evidence reconciliation only.
- The exact docs-inclusive final head SHA and its exact green CI run are recorded in the mutable PR body after CI completes; embedding a future run id in this file would itself mutate the head it describes.

## Telemetry Contract Reconciliation

D-013 remains unchanged: retain raw telemetry for 30 days, admit at most 120 events/minute/client/video, persist no IP address or derived IP identifier, and keep telemetry best-effort.

The final design uses two independent controls:

1. **Per-client event quota** — authenticated callers key by verified user id; anonymous callers key by a digest of a stable server-signed telemetry cookie. Each client/video receives its own 120-event/minute budget.
2. **Anonymous identity-mint circuit breaker** — only requests that force the server to mint a fresh anonymous identity consume the short-lived per-video/minute mint guard. This bounds deliberate cookie deletion/rotation without collapsing all legitimate anonymous viewers into one shared event quota.

The circuit breaker is defense in depth against identity churn; it does not redefine the approved client quota. No raw IP or IP-derived identifier is stored.

## Validation Added For The Final Telemetry Reconciliation

- Existing adversarial playback-event rotation coverage remains: 150 cookie-rotated writes are bounded to 120 accepted writes.
- Existing impression/view rotation coverage remains: ranking counters cannot be inflated without bound through cookie rotation.
- New `test_telemetry_client_policy.py` proves two distinct signed anonymous clients on the same video each receive their own 120-event budget and independently reject the 121st event.
- New policy coverage proves the identity-mint guard remains separate from the per-client event quota.
- `ATLAS_TELEMETRY_SECRET` remains a documented stable non-development contract; missing production configuration fails anonymous telemetry closed while authenticated telemetry remains available.

## Blocker Reconciliation

| Finding | Resolution |
|---|---|
| B1 public comment identity | Public comment responses use a generic viewer label. |
| B2 visibility drift | Shared discoverable/direct-link predicates cover moderation and tombstones across feeds, search, channels, subscriptions, history, and playlists. |
| B3 publish-before-commit | Upload and Studio queueing commit durable dispatch intent before broker publication; reconciliation exists through `make processing-reconcile`. |
| B4 manual process publication | The manual process route uses the same canonical durable publisher. |
| B5 anonymous telemetry trust | Signed anonymous per-client identity preserves the 120/min/client/video contract; a separate identity-mint guard bounds cookie rotation without globally throttling established viewers. |
| B5b telemetry secret contract | `ATLAS_TELEMETRY_SECRET` is documented; non-development anonymous telemetry fails closed when it is absent. |
| B6 counter races | Reaction and telemetry writes use conflict-safe inserts and atomic counter updates. |
| B7 playlist positions | Playlist rows are locked and the next position derives from `MAX(position)`, with middle-delete regression coverage. |
| B8 stale evidence | Canonical ledger and this audit now point at `c5140fc` / `903a3b1`; final docs-head SHA and exact-head CI are recorded in the PR body after the run completes. |

## Historical Green Evidence

Before the final D-013-preserving reconciliation, candidate `266b4600a3973753357a46800c96460aae2cbcfc` passed CI run `34201068181`, and docs head `ec5bf58f54b2b9ba72513f4dfbd32a11b84b0cf8` passed exact-head CI run `34201577602`. Those runs are historical evidence only and do not qualify the new final head.

## Final Gate

Merge is allowed only when all of the following are true at the docs-inclusive final head:

- GitHub reports PR #12 mergeable/clean and non-draft.
- The exact final head has a completed successful CI run.
- The reopened telemetry and release-evidence review threads are resolved against the D-013-preserving implementation.
- Issue #10 is closed only after that exact-head qualification.

## Evidence Boundaries

This record is merge-readiness evidence only. It does not prove deployment, authenticated admin-role browser qualification, or production behavior. Production: `UNVERIFIED`.
