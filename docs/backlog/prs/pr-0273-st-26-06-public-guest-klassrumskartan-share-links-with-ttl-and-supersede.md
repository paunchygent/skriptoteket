---
type: pr
id: PR-0273
title: "ST-26-06 public guest Klassrumskartan share links with TTL and supersede"
status: ready
owners: "agents"
created: 2026-04-30
updated: 2026-04-30
stories:
  - "ST-26-06"
tags: ["frontend", "backend", "klassrumskartan", "public-access", "sharing"]
dependencies:
  - "PR-0274"
  - "ADR-0079"
  - "ADR-0080"
  - "ADR-0084"
  - "REV-ST-26-06"
acceptance_criteria:
  - "Given `ADR-0084` is accepted, when implementation planning starts, then this public guest share slice stays inside the accepted exception and does not create any wider durable anonymous guest artifact path."
  - "Given a public guest opens the grouping or seating export menu, when they inspect export actions, then `Dela länk` appears beside PDF/Excel."
  - "Given a guest clicks `Dela länk`, when pending browser-owned state exists, then the public export preparation path flushes current draft and smart-rule state before share creation."
  - "Given the public helper receives a share request, when `expected_revision` does not match the browser-owned snapshot draft revision, then it rejects with the same strict conflict behavior as public export."
  - "Given the public helper creates a share, when the response returns, then the share has an expiry no later than 60 days and returns a public `/share/classroom/{token}/{slug?}` URL."
  - "Given the public helper creates a share, when the request attempts to set or persist a longer expiry, then the backend rejects it or clamps it to the 60-day ceiling with tested behavior."
  - "Given public guest sharing is implemented, when routes are registered, then creation stays on dedicated public helper routes and anonymous reads stay on the shared public token route without owner-scoped APIs, SPA shell fallback, or account authority."
  - "Given the browser still holds a previous guest share revoke secret for the same snapshot and draft kind, when a newer `Dela länk` succeeds, then the previous guest share is revoked or superseded."
  - "Given the browser does not hold a previous revoke secret, when a newer guest link is created, then the old link remains available only until its natural expiry."
  - "Given a guest later signs in, when authenticated guest-upgrade runs, then guest share links do not silently become account-owned artifacts unless a later explicit story adds that migration."
  - "Given public share creation stores anonymous artifacts, when limits are enforced, then share-specific request-byte caps, rendered-size caps, creation rate limits, active-share ceilings, purge cadence, and redacted metrics/log fields are tested."
  - "Given a browser retries or double-clicks `Dela länk`, when the same client operation is replayed, then share creation and previous-link supersede behavior are idempotent and race-safe."
---

## Problem

Public Klassrumskartan users also need shareable digital links, but guest mode
cannot rely on account ownership, Vault, or owner-scoped APIs. The feature must
stay cookie-agnostic and browser-owned until explicit authentication.

## Goal

Add public guest share-link publishing through the public helper creation
boundary, reusing the authenticated share artifact/read model while applying a
guest-safe TTL ceiling, abuse controls, and browser-held supersede/revoke
behavior. `ADR-0084` is accepted; implementation must stay inside that accepted
exception and the retained `REV-ST-26-06` guardrails.

## Non-goals

- No account-style guest share dashboard.
- No indefinite guest links.
- No owner-scoped API fallthrough.
- No automatic migration of guest shares into an account.
- No public editing or live draft sharing.

## Implementation Plan

1. Add public helper endpoints:
   - `POST /api/v1/public/apps/classroom.group-seating-studio/grouping/share`
   - `POST /api/v1/public/apps/classroom.group-seating-studio/seating/share`
2. Reuse public export snapshot materialization and strict expected-revision
   validation; create no artifact when the revision guard fails.
3. Reuse the share artifact storage/read route from `PR-0274`, with
   `owner_user_id = null`, `source = public_guest`, and `expires_at` no later
   than `created_at + 60 days`.
4. Generate a browser-held revoke secret for public guest shares and store only
   its hash server-side.
5. Let the browser pass the previous revoke secret for the same guest
   snapshot/draft kind so the server can revoke/supersede the older guest link.
6. Store latest public guest share metadata locally in the browser per snapshot
   plus draft kind.
7. Add guest export-menu UI for `Dela länk`, copy-link feedback, expiry
   messaging, and newest-link replacement behavior.
8. Add client operation ids or idempotency keys so retries, double-clicks, and
   two-tab races do not create contradictory "newest link" state.
9. Model previous-link supersede as an atomic conditional update keyed by
   previous token hash plus revoke-secret hash. Invalid previous secrets should
   not block new share creation, but must be logged through redacted reason
   codes and must not claim the older link was revoked.
10. Add share-specific abuse-control settings and repository constraints:
    - maximum request bytes
    - maximum rendered artifact bytes
    - maximum share creations per IP/window
    - maximum active guest shares per snapshot fingerprint or coarse IP bucket
      where feasible
    - expired-row purge command or scheduled operator path
    - metrics/log counters that avoid raw class, room, group, or student values
11. Ensure public helper logging/metrics use `public_helper_*` reason codes and
   do not retain raw student payloads.
12. Render from the canonical validated presentation model created by the
    export/snapshot materialization path. Persist renderer version,
    presentation schema version, presentation hash or immutable provenance, and
    content hash; never accept browser-supplied HTML, CSS, or preview metadata
    as the artifact source.

## Test Plan

- Backend tests for cookie-agnostic public share creation, payload caps,
  expected-revision conflicts, 60-day expiry ceiling, revoke-secret hashing, and
  supersede behavior.
- Backend tests asserting public guest shares cannot request or persist an
  expiry beyond the 60-day ceiling.
- Backend tests for payload-too-large, rendered-artifact-too-large,
  rate-limited, active-share ceiling, expired-share purge, no owner-scoped row
  creation, ambient-cookie ignoring, and rejected account identifiers.
- Route tests proving helper creation routes ignore ambient sessions and public
  token read routes avoid owner-scoped APIs, SPA shell fallback, and account
  authority.
- Renderer/provenance tests proving hostile class, room, group, and student
  values are escaped in body text, title, preview metadata, and CSS-adjacent
  contexts, with renderer/schema/hash fields persisted.
- Backend tests for retry idempotency, invalid previous secret fallback,
  double-create races, and active-link counting for the same snapshot/draft
  kind.
- Frontend tests for guest export menu placement, snapshot flush before share
  creation, copy-link UI, previous-link revoke payload, and
  missing-revoke-secret fallback.
- Anonymous browser proof for public grouping and seating share creation,
  opening links, and confirming no authenticated API calls occur.
- Regression proof that public PDF/Excel export behavior is unchanged.
- `pdm run lint`
- `pdm run typecheck`
- `pdm run docs-validate`
- `pdm run handoff-validate` if `.codex/handoff.md` records live UI proof.
- `git diff --check`

## Rollback Plan

Hide the public guest `Dela länk` action and disable public share creation.
Existing guest share artifacts can expire naturally or be administratively
revoked if the share route itself must be disabled.
