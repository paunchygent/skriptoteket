---
type: adr
id: ADR-SKRIPT-0084
title: Klassrumskartan public share artifact exception
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: accepted
links:
  governing:
  - ADR-SKRIPT-0079
  - ADR-SKRIPT-0080
  - EPIC-SKRIPT-26
  - ST-SKRIPT-26-06
deciders:
- user-lead
retired_ids:
- ADR-0084
---

## Context
`ADR-0079` keeps public curated-app guest state browser-owned before login. It
allows stateless helper work, direct rendering, and transient buffers, and it
explicitly keeps guest export direct-download and Vault/MyFiles-free.

`ST-26-06` proposes `Dela länk` as an export variant for Klassrumskartan. The
authenticated lane can store teacher-owned immutable share artifacts, but the
public guest lane would create durable anonymous server-side artifacts with
60-day expiry. That is not authorized by the current accepted public-boundary
text.

## Decision
This ADR authorizes one narrow exception to `ADR-0079`: Klassrumskartan public
guests may publish immutable, anonymous share artifacts only through dedicated
public helper creation routes and only for the `Dela länk` export variant.
Anonymous reads use the shared public token route, for example
`/share/classroom/{token}/{slug?}`, and that read route is not an authenticated,
owner-scoped, or SPA-shell fallback surface.

The exception contract is:

- The browser remains the source of truth for editable guest work.
- The server-stored artifact is a published export artifact, not a guest
  workspace, draft, history row, job, Vault file, or account-owned record.
- Public helper creation routes must be cookie-agnostic and ignore ambient
  sessions.
- Public helper creation routes must reject owner-scoped identifiers and must
  not create owner-scoped rows.
- Public token read routes must resolve only by unguessable token authority and
  must not call owner-scoped APIs or depend on account authority.
- The server must render public guest share artifacts from a canonical,
  validated presentation model produced by the export/snapshot materialization
  path. It must not accept browser-supplied HTML, CSS, or preview metadata as
  the artifact source.
- The artifact stores only sanitized presentation data or immutable provenance,
  rendered output needed for the immutable public page, hashed authority tokens,
  renderer version, presentation schema version, presentation hash or equivalent
  immutable provenance, content hash, and redacted operational metadata.
- Guest share artifacts expire no later than 60 days after creation unless a
  later accepted ADR explicitly changes that ceiling.
- Guest share artifacts are excluded from authenticated guest-upgrade import and
  must not silently become account-owned artifacts after sign-in.
- Browser-held revoke/supersede secrets are best-effort controls, not account
  management.
- Expired/revoked guest share artifacts must be purgeable through a documented
  operator path.

## Non-Decisions
The source record did not define a separate section for this package heading.

## Consequences
- `PR-0273` can start once its remaining planning and dependency gates are
  green, and must implement this accepted exception without widening it.
- Public guest share storage needs share-specific rate limits, payload and
  rendered-size caps, quotas or creation ceilings, purge cadence, and redacted
  metrics/log proof.
- Backend tests must prove public guest shares cannot request or persist an
  expiry beyond the 60-day ceiling.
- Renderer tests must prove hostile class, room, group, and student values are
  escaped in body text, title, preview metadata, and CSS-adjacent contexts.
- Route tests must prove public helper creation ignores ambient sessions and
  public token reads avoid owner-scoped APIs, SPA shell fallback, and account
  authority.
- Share pages can include class, room, group, and student display names, so
  public read routes need an explicit privacy/indexing contract:
  `noindex,nofollow`, sitemap exclusion, escaped preview metadata, and careful
  cache semantics for active/revoked/expired pages.
- This exception does not change public guest import preview, Smart helpers, or
  direct-download PDF/Excel export behavior.
