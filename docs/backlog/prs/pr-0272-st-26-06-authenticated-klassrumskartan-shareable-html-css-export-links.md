---
type: pr
id: PR-0272
title: "ST-26-06 authenticated Klassrumskartan shareable HTML/CSS export links"
status: ready
owners: "agents"
created: 2026-04-30
updated: 2026-04-30
stories:
  - "ST-26-06"
tags: ["backend", "frontend", "klassrumskartan", "export", "sharing"]
dependencies:
  - "ST-26-06"
  - "ADR-0075"
  - "ADR-0079"
  - "REV-ST-26-06"
acceptance_criteria:
  - "Given an authenticated teacher opens the grouping or seating export menu, when they inspect the export actions, then `Dela länk` appears beside PDF/Excel."
  - "Given an authenticated teacher clicks `Dela länk`, when pending draft or smart-rule state exists, then the same export preparation/save guard used by PDF/Excel completes and the post-flush `expected_revision` is sent before share creation."
  - "Given an authenticated share request carries a stale `expected_revision`, when the handler validates the draft immediately before rendering, then it returns `409 CONFLICT` and creates no share artifact row."
  - "Given the backend creates a share artifact, when the response returns, then the teacher receives a copyable `/share/classroom/{token}/{slug?}` URL."
  - "Given anyone opens the share URL, when the artifact is active, then the response renders immutable responsive HTML/CSS with no app chrome, editor controls, owner-scoped ids, or live API calls."
  - "Given the teacher owns share artifacts, when they view existing shares for a draft, then they can copy and revoke them."
  - "Given a share is revoked, when the public URL is opened, then it returns a calm unavailable/expired page rather than the plan."
  - "Given the source draft, roster, room template, or owner account is deleted/deactivated, when owned shares are listed or read, then the lifecycle rule for archive, revoke, or purge is deterministic and tested."
---

## Problem

Authenticated Klassrumskartan exports create files, but teachers need a durable
web link suitable for Teams, Google Classroom, and LMS posts. The feature should
not create a live draft link or expose owner-scoped APIs publicly.

## Goal

Add authenticated share-link publishing as an export-menu action backed by
immutable server-rendered HTML/CSS artifacts. This slice is ready after
`REV-ST-26-06` re-review approval; the public guest share slice remains separate
under `PR-0273` and the accepted `ADR-0084` exception.

## Non-goals

- No live collaborative editing.
- No public guest share flow in this slice.
- No generic Vault sharing model.
- No raw browser-supplied HTML storage.
- No change to existing PDF/Excel export behavior except adding the new export
  action.

## Implementation Plan

1. Add a share artifact model/table with token hash, owner user id, draft kind,
   title, slug, sanitized presentation payload or immutable provenance,
   renderer version, presentation schema version, presentation hash, rendered
   HTML/CSS content, content hash, created/revoked timestamps, and optional
   expiry.
2. Add application handlers for authenticated grouping/seating share creation.
3. Reuse the existing export preparation paths to build canonical
   grouping/seating presentation data.
4. Add or extract a static HTML/CSS renderer for grouping and seating share
   pages.
5. Add kind-specific authenticated endpoints with typed payloads:
   - `POST /api/v1/apps/classroom.group-seating-studio/drafts/grouping/{draft_id}/share`
   - `POST /api/v1/apps/classroom.group-seating-studio/drafts/seating/{draft_id}/share`
   - `GET /api/v1/apps/classroom.group-seating-studio/drafts/grouping/{draft_id}/shares`
   - `GET /api/v1/apps/classroom.group-seating-studio/drafts/seating/{draft_id}/shares`
   - `POST /api/v1/apps/classroom.group-seating-studio/shares/{share_id}/revoke`
6. Require each create payload to include `expected_revision`; validate it in
   the application handler immediately before rendering, and create share
   metadata only after the validated render succeeds.
7. Add public read route:
   - `GET /share/classroom/{token}/{slug?}`
8. Add export-menu UI action, copy-link state, and simple management/revoke UI
   for authenticated shares.
9. Add metadata and responsive/print CSS requirements to the share template.
10. Add owned-share lifecycle rules:
    - deleting a draft must either keep shares listable from an archive surface
      or revoke them; choose one and test it
    - roster/class or room-template deletion must define whether derived shares
      are kept as immutable artifacts or revoked
    - owner account deletion/deactivation must revoke or purge all owned share
      artifacts through a deterministic service path
11. Add route metadata policy for active, revoked, expired, missing-token, and
    stale-slug responses: status semantics, `noindex,nofollow`, sitemap
    exclusion, escaped preview tags, and cache headers.

## Test Plan

- Backend unit tests for token hashing, owner-scoped create/list/revoke,
  revoked/expired read behavior, slug independence, owner mismatch, deletion
  lifecycle, and no artifact row on `expected_revision` conflict.
- Backend tests for grouping and seating `409 CONFLICT` on stale
  `expected_revision`.
- Renderer tests for responsive HTML metadata, no script/app chrome, print CSS
  presence, and hostile class/room/group/student names escaped in body,
  `<title>`, description, Open Graph, and CSS-adjacent contexts.
- Route tests for active, revoked, expired, missing-token, and stale-slug
  responses asserting status, robots metadata, sitemap exclusion, cache headers,
  and absence of the SPA shell.
- Frontend tests for `Dela länk` export-menu placement, pre-export flush
  behavior, post-flush revision payload, copy-link UI, and revoke UI.
- `pdm run lint`
- `pdm run typecheck`
- Focused backend/frontend tests for the touched share, renderer, and
  export-menu surfaces.
- Live browser proof for creating a share from grouping and seating, opening it
  anonymously, and revoking it.
- `pdm run docs-validate`
- `pdm run handoff-validate` if `.codex/handoff.md` records live UI proof.
- `git diff --check`

## Rollback Plan

Disable the `Dela länk` menu action and revoke new share creation while leaving
existing PDF/Excel exports untouched. Existing share read route can remain
available for already-created artifacts unless a security issue requires
revocation.
