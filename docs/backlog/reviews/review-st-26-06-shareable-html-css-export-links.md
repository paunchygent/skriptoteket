---
type: review
id: REV-ST-26-06
title: "Review: ST-26-06 shareable HTML/CSS export links"
status: approved
owners: "agents"
created: 2026-04-30
updated: 2026-04-30
reviewer: "lead-developer"
stories:
  - ST-26-06
prs:
  - PR-0272
  - PR-0273
adrs:
  - ADR-0075
  - ADR-0079
  - ADR-0080
  - ADR-0084
links:
  - EPIC-26
  - EPIC-35
  - PR-0268
---

## TL;DR

`ST-26-06`, `PR-0272`, and `PR-0273` are approved as a ready planning surface
after re-review and user-lead `ADR-0084` acceptance. The docs now keep public
guest durable share artifacts inside the accepted `ADR-0084` exception, add the
missing authenticated `expected_revision` contract, and spell out
indexing/privacy, lifecycle, abuse-control, provenance, idempotency proof,
renderer authority, TTL ceiling, and public create/read route separation.

## Problem Statement

This review checks whether the two proposed implementation slices cover the
contract conflicts created by turning Klassrumskartan exports into public URLs.
The core risk is accidentally treating share links as "just another export"
while they actually add a durable anonymous public artifact surface.

## Proposed Solution

- `PR-0272` adds authenticated owned share artifacts, public read links,
  renderer/storage, export-menu UI, list/copy, and revoke.
- `PR-0273` reuses that share artifact/read model for public guest snapshots
  with a 60-day TTL ceiling and browser-held revoke/supersede metadata.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/stories/story-26-06-klassrumskartan-shareable-html-css-export-links.md` | Parent story, acceptance criteria, export-boundary claims | 12 min |
| `docs/backlog/prs/pr-0272-st-26-06-authenticated-klassrumskartan-shareable-html-css-export-links.md` | Authenticated implementation plan and proof obligations | 14 min |
| `docs/backlog/prs/pr-0273-st-26-06-public-guest-klassrumskartan-share-links-with-ttl-and-supersede.md` | Public guest implementation plan and public-helper boundary | 14 min |
| `docs/backlog/epics/epic-26-klassrumskartan-explicit-exports-and-class-list-import.md` | Epic-level export contract | 8 min |
| `docs/adr/adr-0079-public-curated-app-access-profiles-and-guest-state-boundaries.md` | Public guest state and export boundary | 12 min |
| `docs/adr/adr-0080-klassrumskartan-guest-smart-parity-and-history-based-smart-boundary.md` | Guest Smart/export/history separation | 6 min |
| `src/skriptoteket/web/api/v1/apps_classroom_planner_seating.py` | Current authenticated seating export route shape | 5 min |
| `src/skriptoteket/web/api/v1/apps_classroom_planner_grouping.py` | Current authenticated grouping export route shape | 5 min |
| `src/skriptoteket/web/api/v1/public_apps_classroom_planner_exports.py` | Current public helper limits and route shape | 8 min |
| `src/skriptoteket/web/routes/spa_fallback.py` / `src/skriptoteket/web/spa_metadata.py` | Public route indexing and fallback behavior | 8 min |

**Total estimated time:** ~92 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Put `Dela länk` in the existing export menu | Matches EPIC-26 and avoids a parallel sharing workflow | [x] |
| Use unguessable tokens with cosmetic slugs | Correct authority split; slugs must never authorize access | [x] |
| Store authenticated shares as durable teacher-owned artifacts | `PR-0272` now requires lifecycle/delete/deactivation rules and proof | [x] |
| Let public guests create 60-day server-stored share artifacts under ADR-0079 | Not under `ADR-0079` alone; accepted `ADR-0084` is the narrow exception authority for `PR-0273` | [x] |
| Treat the current PR-0272 endpoint shape as implementation-ready | `PR-0272` now uses kind-specific routes plus typed `expected_revision` proof | [x] |
| Treat PR-0273 abuse controls as specified enough | `PR-0273` now requires share-specific limits, size caps, purge, metrics/log redaction, and race/idempotency tests | [x] |

## Review Checklist

- [x] Scope is bounded to Klassrumskartan share links
- [x] Authenticated and public guest slices are separated
- [x] Public guest persistence is governed by the accepted `ADR-0084` exception
- [x] Authenticated share creation has a request/route shape that can enforce
      draft kind and expected revision
- [x] Public read route metadata, robots policy, and sitemap posture are explicit
- [x] Share artifact retention, purge, and deletion semantics are specified
- [x] Supersede/revoke behavior is idempotent and race-safe
- [x] Tests prove malicious roster/classroom/student text is escaped in HTML,
      title, description, and share metadata

## Review Feedback

**Reviewer:** `lead-developer`
**Date:** `2026-04-30`
**Verdict:** `approved after re-review`

### Required Changes

Closed by the 2026-04-30 re-review. The original findings remain below as the
audit trail for what was remediated.

1. **Blocker: public guest share persistence is not authorized by the accepted public boundary.**

   `PR-0273` creates durable server-side public guest share artifacts with
   `owner_user_id = null`, `source = public_guest`, and `expires_at =
   created_at + 60 days`. That is a real anonymous persistence surface, not the
   current direct-download helper model. `ADR-0079` says browser-owned guest
   state remains authoritative, the server may only perform stateless helper
   work or direct rendering before login, and guest export may use transient
   buffers only rather than durable guest artifacts.

   Fix: before implementing `PR-0273`, amend `ADR-0079` or add a reviewed
   decision section to `ST-26-06` that explicitly authorizes a narrow
   "published public share artifact" exception. The exception must define the
   table boundary, TTL, purge, abuse controls, logging redaction, no
   owner-scoped fallback, and no automatic guest-upgrade migration.

   Proof requirement: docs review approval plus backend tests showing public
   share creation ignores ambient cookies, creates no owner-scoped rows, and
   rejects attempts to attach account identifiers.

2. **Blocker: `PR-0272` cannot enforce the story's expected-revision export contract as written.**

   `ST-26-06` requires the same pre-export persistence contract as PDF/Excel,
   including `expected_revision` validation before metadata is created. The
   proposed authenticated route is `POST
   /api/v1/apps/classroom.group-seating-studio/drafts/{draft_id}/share`; it
   does not carry draft kind, expected revision, or a typed share-creation
   payload. The existing authenticated export-job endpoints are draft-kind
   specific (`/drafts/seating/{draft_id}/exports/jobs` and
   `/drafts/grouping/{draft_id}/exports/jobs`) and their job-creation handlers
   load the current server draft after the frontend save flush. If share
   creation copies that shape, a stale tab or post-flush race can publish a
   newer server state than the user thought they shared.

   Fix: make share creation a first-class contract, not a generic draft action:
   add kind-specific routes or an explicit `draft_kind` discriminator, require
   `expected_revision`, and validate it in the application handler immediately
   before rendering. Create share metadata only after the validated render
   succeeds.

   Proof requirement: backend tests for grouping and seating `409 CONFLICT`
   when `expected_revision` mismatches, frontend tests proving the post-flush
   revision is sent, and an assertion that no share artifact row is created on
   conflict.

3. **High: share-link indexing and preview metadata are under-specified for pages that can expose student names.**

   The story requires stable title/description metadata for Teams, Google
   Classroom, and LMS previews, but it never decides robots policy, canonical
   policy, sitemap exclusion, or cache behavior. Current launch metadata only
   makes `/` and `/public/apps/classroom.group-seating-studio` indexable; private
   routes and unknown routes are explicitly non-indexable. Share pages will
   likely contain class names, room names, and student display names, so
   "metadata works for link previews" must not silently become "search engines
   may index roster pages."

   Fix: add a share-route metadata contract. Default recommendation:
   `noindex,nofollow`, no sitemap entry, no canonical URL beyond the exact token
   URL, Open Graph/Twitter metadata escaped from sanitized presentation fields,
   and conservative `Cache-Control` for revoked/expired pages.

   Proof requirement: route tests for active, revoked, expired, missing-token,
   and stale-slug responses that assert status, robots metadata,
   sitemap exclusion, and absence of the SPA shell.

4. **High: public share abuse controls and cleanup are named but not specified.**

   `PR-0273` says "TTL, abuse controls" and `public_helper_*` logging, but the
   concrete implementation plan does not define share-specific rate limits,
   payload caps, total stored bytes, per-browser/IP creation ceilings, purge
   cadence, or administrative cleanup. The existing public helper settings are
   named around import preview and Smart runs, with `PUBLIC_HELPER_SMART_RUN_*`
   currently reused by public export routes. That is too blurry for a durable
   public storage feature.

   Fix: add share-specific settings and repository constraints:
   max request bytes, max rendered artifact bytes, max shares per window,
   max active guest shares per fingerprint/IP bucket if feasible, expired-row
   purge command or scheduled operator path, and metrics/log counters that avoid
   retaining raw student payloads.

   Proof requirement: unit/API tests for payload-too-large, rate-limited,
   rendered-artifact-too-large, expired-share purge, and redacted log/metric
   fields.

5. **High: authenticated share lifecycle is missing deletion and ownership semantics.**

   `PR-0272` creates durable teacher-owned shares without default expiry, but it
   does not define what happens when the source draft, roster, room template, or
   owner account is deleted/deactivated. Because the artifact is frozen and
   public, this can leave public roster pages available after the teacher thinks
   the source class/workspace is gone.

   Fix: specify lifecycle rules before implementation. At minimum, decide
   whether deleting a draft leaves its shares listable from an archive surface,
   whether roster/class deletion revokes derived shares, and how account
   deletion/deactivation revokes or purges owned share artifacts.

   Proof requirement: backend tests for draft deletion, roster/template deletion
   if supported, owner mismatch, and revoke-all/account cleanup behavior.

6. **Medium: storing rendered HTML/CSS without a versioned sanitized source model weakens auditability.**

   The plan stores `HTML/CSS content` and a `content hash`, while separately
   saying browser-supplied HTML must never be accepted. That still leaves the
   durable artifact as an opaque string unless the stored record also carries a
   renderer version and a sanitized canonical presentation payload or payload
   hash. Without that, a future escaping/CSP fix cannot identify which artifacts
   were rendered with an old renderer, and tests can miss title/meta injection
   even if body markup is escaped.

   Fix: persist `renderer_version`, `presentation_schema_version`,
   `source_kind`, `presentation_hash`, and either the sanitized presentation
   payload or enough immutable provenance to audit the exact renderer input.
   Keep rendered HTML immutable after publish unless an explicit security
   migration revokes or re-renders artifacts.

   Proof requirement: renderer tests with hostile class names, room names, group
   labels, and student names in body text, `<title>`, description, Open Graph,
   and CSS-adjacent contexts; assert no `<script>`, inline event handlers,
   external app APIs, or owner-scoped IDs.

7. **Medium: browser-held guest supersede/revoke needs race and idempotency semantics.**

   `PR-0273` lets the browser pass the previous revoke secret so a newer guest
   share can supersede the old one. The plan does not define what happens on
   double-clicks, retries after network failure, two tabs sharing the same local
   metadata, an invalid previous secret, or two concurrent creates for the same
   snapshot/draft kind. Without atomic conditional updates, the UI can claim
   "newest link only" while multiple active links remain.

   Fix: add an idempotency key or client operation id, a stable `superseded`
   status, and an atomic conditional revoke/update path keyed by previous token
   hash plus revoke-secret hash. Invalid previous secret should not block new
   share creation unless the product explicitly wants strict replacement.

   Proof requirement: backend tests for retry idempotency, invalid previous
   secret fallback, double-create races, and active-link counting for the same
   snapshot/draft kind.

### Suggestions

- Add generated OpenAPI/frontend contract refresh to `PR-0272` and `PR-0273`
  closeout if the new endpoints are exposed through OpenAPI.
- Prefer a dedicated share module (`classroom_planner_shares`) rather than
  extending the existing export-job modules; this is a publish/read/revoke
  lifecycle, not a recoverable Vault-backed download job.
- Keep unavailable pages calm, but make status semantics explicit: `404` for
  unknown token, `410` or a documented `200` unavailable page for revoked/expired
  tokens, and tests locking the choice.

### Re-review Closure

**Reviewer:** `lead-developer`
**Date:** `2026-04-30`
**Verdict:** `approved`

- Finding 1 was originally closed by draft `ADR-0084`, `ST-26-06` blocked
  status, and `PR-0273`'s explicit stop condition. It is now governed by
  accepted `ADR-0084`, and `PR-0273` is ready only within that exception.
- Finding 2 is closed by `PR-0272`'s kind-specific grouping/seating share routes,
  required `expected_revision`, immediate pre-render validation, and no-row-on-
  conflict proof.
- Finding 3 is closed by `ST-26-06` and `PR-0272` privacy-first route metadata
  requirements: `noindex,nofollow`, sitemap exclusion, escaped preview tags,
  status semantics, and cache headers.
- Finding 4 is closed by `PR-0273`'s share-specific request/rendered-size caps,
  rate limits, active-share ceilings, purge path, and redacted metric/log proof.
- Finding 5 is closed by `PR-0272`'s owned-share lifecycle requirements for
  source draft, roster/class, room-template, and account deletion/deactivation.
- The two medium findings are also closed by the added renderer/provenance
  fields and guest idempotency/race-safety requirements.

The original implementation stop condition is closed by accepted `ADR-0084`. If
`ADR-0084` changes materially later, re-open this review or create the required
ADR-targeted review follow-up before implementing the changed contract.

### ADR-0084 Acceptance Review Addendum

**Reviewer:** `lead-developer`
**Date:** `2026-04-30`
**Verdict:** `changes_requested for accepting ADR-0084`

The ADR acceptance review found three guardrails that must live in the ADR
decision text before the proposed exception can unblock public guest share
implementation:

1. Lock renderer provenance at the ADR level: public guest artifacts must be
   rendered server-side from a canonical validated presentation model, must not
   accept browser-supplied HTML/CSS/metadata, and must persist renderer version,
   presentation schema/hash or immutable provenance, and hostile-value escaping
   proof for body, title, preview metadata, and CSS-adjacent contexts.
2. Make the 60-day public guest TTL a hard ceiling, not only a default, unless
   a later accepted ADR changes that ceiling.
3. Separate public helper creation routes from the anonymous public token read
   route so the accepted exception does not blur cookie-agnostic publish
   expectations with token-only read behavior.

Remediation applied: `ADR-0084`, `ST-26-06`, and `PR-0273` now carry these
guardrails. This finding set was superseded by the acceptance re-review below.

### ADR-0084 Acceptance Re-review

**Reviewer:** `lead-developer`
**Date:** `2026-04-30`
**Verdict:** `approved for user-lead ADR acceptance`

The three ADR acceptance findings are closed:

- `ADR-0084` now requires server-side rendering from a canonical validated
  presentation model, rejects browser-supplied HTML/CSS/preview metadata as the
  artifact source, and requires renderer/schema/hash or immutable-provenance
  fields plus hostile-value escaping proof.
- `ADR-0084`, `ST-26-06`, and `PR-0273` now treat 60 days as the public guest
  share expiry ceiling rather than a configurable default.
- `ADR-0084`, `ST-26-06`, and `PR-0273` now separate cookie-agnostic public
  helper creation routes from anonymous token read routes, and require read
  routes to avoid owner-scoped APIs, SPA-shell fallback, and account authority.

The user-lead accepted `ADR-0084` after this re-review. `PR-0273` is now ready
and must stay inside the accepted exception.

### ADR-0084 User-lead Acceptance Alignment

**Date:** `2026-04-30`
**Decision:** `ADR-0084 accepted`

Docs state is aligned to the decision: `ADR-0084` is accepted, `ST-26-06` and
`PR-0273` are ready, and public guest durable share artifacts are governed by
the accepted exception rather than blocked on a proposed decision.

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `REV-ST-26-06` | Recorded a retained changes-requested review for the ST-26-06 / PR-0272 / PR-0273 share-link planning surface. |
| 2 | `ADR-0084` | Added the public share artifact exception, later accepted by the user-lead after re-review. |
| 3 | `ST-26-06` | Added the `ADR-0084` dependency, privacy/indexing requirements, and public-guest authority acceptance criteria; later moved the story to ready after ADR acceptance. |
| 4 | `PR-0272` | Added kind-specific routes, `expected_revision`, lifecycle, provenance, metadata, and deletion proof requirements; re-review moved the authenticated slice back to ready. |
| 5 | `PR-0273` | Added concrete abuse-control, purge, idempotency, and race-safety requirements; later moved the public guest slice to ready after accepted `ADR-0084`. |
| 6 | `REV-ST-26-06` | Re-reviewed the remediation and approved the planning surface while retaining the then-active `ADR-0084` implementation stop condition for public guest shares. |
| 7 | `ADR-0084`, `ST-26-06`, `PR-0273`, `REV-ST-26-06` | Applied the ADR acceptance review guardrails for renderer provenance, 60-day TTL ceiling, and public helper creation versus anonymous token read route separation. |
| 8 | `REV-ST-26-06` | Re-reviewed the ADR-0084 acceptance guardrail remediation and approved the ADR for user-lead acceptance while keeping `PR-0273` blocked until the ADR status changes. |
| 9 | `ADR-0084`, `ST-26-06`, `PR-0273`, `EPIC-26`, `.codex/handoff.md`, `docs/index.md` | Aligned docs to user-lead ADR acceptance: `ADR-0084` accepted, `ST-26-06` and `PR-0273` ready, and stale proposed/blocking wording removed from live guidance. |
