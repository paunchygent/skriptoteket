---
type: epic
id: EPIC-SKRIPT-36
title: Klassrumskartan scoped sharing and authenticated import
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: proposed
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
links:
  decisions:
  - ADR-SKRIPT-0079
  - ADR-SKRIPT-0084
outcome: Klassrumskartan share links and current-link management are scoped by roster
  fingerprints, with seating prepared to add classroom context, while later authenticated
  import/discovery focuses on reusable roster and classroom-template assets rather
  than short-lived grouping or seating snapshot state.
retired_ids:
- EPIC-36
dependencies:
- EPIC-SKRIPT-26
---

## Scope

### Source: Scope

- Establish a class-first current-share scope for Klassrumskartan:
  - grouping current-link scope: `roster_fingerprint + draft_kind`
  - seating current-link scope: `roster_fingerprint + classroom_fingerprint + draft_kind`
- Use `roster_fingerprint` as the canonical term for the portable class-list
  identity. It represents the class content teachers experience as a class, but
  avoids introducing a second drift-prone term beside the existing domain
  object.
- Define `roster_fingerprint` from normalized roster name plus normalized
  student display-name membership. Roster name is part of identity because
  rosters may be course-based rather than strictly class-based, and the same
  teacher can have several courses with the same students. Local student ids
  must not be part of the portable scoped-sharing fingerprint.
- Student order must not affect `roster_fingerprint`; use a sorted multiset of
  normalized student display names with duplicates preserved.
- Name normalization must stay conservative in the first fingerprint version:
  trim/collapse whitespace, Unicode-normalize to NFC, and case-fold for hash
  input, without accent stripping, punctuation removal, name reordering, or
  nickname matching.
- Apply the same normalization profile to roster names and student display
  names.
- Implement fingerprinting behind an injected policy/service boundary rather
  than duplicating normalization helpers across routes, repositories, frontend
  flows, and import handlers.
- Authenticated scoped sharing must compute `roster_fingerprint`
  server-side from the loaded draft/roster, not trust a frontend-submitted
  fingerprint.
- Public guest mode may use browser-side fingerprints for local UX metadata, but
  public helper persistence must recompute or validate server-relevant
  fingerprints from the submitted snapshot before storing scope state.
- Preserve immutable share artifacts as exported presentation snapshots. The
  scope key points to the newest active artifact for a teacher-relevant object;
  it is not the artifact identity, content hash, token, or authorization secret.
- Make different classes able to hold different current grouping and seating
  share links at the same time.
- Keep authenticated sharing durable, owner-aware, listable, copyable, and
  revocable while moving current-link management toward semantic class/classroom
  scope instead of account-wide or browser-only state.
- Keep public guest sharing intentionally narrower:
  - no public discovery surface
  - no public import flow
  - no account-style guest dashboard
  - browser-held revoke metadata may use class-scoped keys where feasible, but
    public mode must stay inside the accepted `ADR-SKRIPT-0084` exception.
- Prepare authenticated teacher-to-teacher import and discovery for verified
  organization/domain contexts around reusable assets:
  - shared class lists / rosters
  - shared classroom templates
  - import or copy semantics instead of live collaborative editing.
- Keep grouping and seating snapshots as shareable/exported artifacts, not
  planned import/discovery objects, unless a later reviewed story demonstrates
  concrete user value.
- Distinguish link sharing from import/discovery:
  - anonymous token links render immutable artifacts
  - authenticated import flows create or reuse account-owned class/classroom
    assets under explicit teacher control.
- Keep later classroom-aware seating compatible with teachers sharing one
  reusable classroom template across several classes while each class retains
  its own seating arrangement for that room.
- Seating share creation requires a selected classroom/template. Seating drafts
  may exist without a template, but `Dela länk` must be disabled or explain that
  a classroom must be selected before sharing.
- Define `classroom_fingerprint` as the portable classroom-template identity for
  authenticated classroom-template import/discovery and seating share scope. It
  includes normalized template name plus normalized room geometry, not the local
  template row id.

### Source: Out of Scope

- Replacing the existing `ST-SKRIPT-26-06` immutable share-page contract.
- Live collaborative editing or public owner-scoped draft APIs.
- Public guest import/discovery or cross-browser guest sync.
- Treating e-mail domain matching as sufficient authorization without an
  approved organization/realm policy.
- Finalizing tenant, school, or domain membership rules in this epic draft.
- Requiring classroom context for grouping, which remains class-first and may
  be classroom-agnostic.
- Migrating existing share artifacts in the planning slice; migration belongs
  to a later PR task after the target schema is reviewed.

## Epic Contract

### Source: Product Rules

- The class remains the primary pedagogical anchor.
- `roster_fingerprint` is the canonical scope term for class-list identity; this
  epic does not introduce a separate durable Class aggregate.
- `roster_fingerprint` includes roster name and normalized student membership.
  Name-only changes therefore intentionally create a different portable roster
  identity until a later reviewed story defines aliases or merges.
- Future stable student ids from a central school/organization roster may become
  part of a later fingerprint version, but that identity model is out of scope
  until an authenticated school/org roster story defines it.
- `classroom_fingerprint` uses normalized room/template name plus canonicalized
  grid, seat, zone, and fixture geometry. Local seat/fixture/template ids must
  not affect the portable fingerprint unless a later reviewed model gives them
  semantic identity.
- Fixture labels are included when present and normalized through the same
  conservative profile; the fingerprint must not infer label aliases.
- Conceptually:
  `classroom_fingerprint = hash(normalized_template_name, canonical_room_geometry)`.
- Grouping and seating are separate share scopes for the same class.
- Grouping share scope never includes `classroom_fingerprint`. Classroom context
  may influence the grouping logic before sharing, but it is not part of the
  grouping share presentation identity.
- Seating sharing is roster-and-classroom scoped.
- A current-link scope may advance to a newer artifact when the teacher shares
  again, but older immutable artifacts must keep their token identity until
  revoked, expired, or explicitly superseded by lifecycle policy.
- Authenticated re-share moves the current pointer for the scope only; it must
  not automatically revoke older authenticated links. Older authenticated links
  stay active until explicit teacher revoke or lifecycle revocation.
- Store the authenticated current link as a separate pointer model, not as a
  mutable property of the immutable share artifact. Artifacts may store scope
  metadata for audit/query, but the pointer row owns "current for this scope".
- Public guest mode can improve local browser coherence by using class-scoped
  browser metadata, but authenticated sharing/import is the long-term coherent
  path.
- Authenticated import must be non-destructive by default: shared artifacts
  should be imported or copied into the receiving teacher's account rather than
  mutating the source teacher's draft or assets.

## ADR Coverage

The source does not record separate ADR coverage.

## Contract Inputs

### Source: Dependencies

- [Klassrumskartan product direction](../../reference/ref-skript-general-klassrumskartan-product-direction-2026-03-21-klassrumskartan-product-direction-2026-03-21.md)
- [Scoped sharing reference](../../reference/ref-skript-general-klassrumskartan-scoped-sharing-and-import-direction-klassrumskartan-scoped-sharing-and-import-direction.md)
- [EPIC-24: Klassrumskartan fundamentals recovery](epic-24-group-seating-studio-slice-2.md)
- [EPIC-SKRIPT-26: explicit exports and share links](epic-skript-26-klassrumskartan-explicit-exports-and-class-list-import.md)
- [EPIC-32: public curated-app access foundation](epic-32-public-curated-app-access-foundation-and-klassrumskartan-demo.md)
- [ST-SKRIPT-26-06: shareable HTML/CSS export links](../stories/st-skript-26-06-klassrumskartan-shareable-html-css-export-links.md)

## Stories

### Source: Candidate Story Stack

- Define and review the current-share scope-key contract for authenticated
  grouping and seating.
- Apply class-fingerprint-scoped current-link management for authenticated
  grouping and seating share lists.
- Align public guest browser metadata with class-scoped keys without adding
  public discovery, import, or server-side listing.
- Add classroom-fingerprint seating scope fields behind an accepted schema and
  migration plan.
- Define authenticated organization/domain discovery policy for shared
  Klassrumskartan assets.
- Add authenticated import/copy flows for shared class lists and classroom
  templates.
- Reassess grouping/seating snapshot import only if later product evidence shows
  durable value beyond sharing an immutable link.

## Epic Verification Plan

### Source: Review Gate

This epic is proposed. It needs review before implementation begins, especially
around scope-key persistence, existing share-artifact migration, organization
membership, privacy, and the public guest boundary.

## Exceptions And Follow-Ups

The source records no separate approved exception or follow-up.

## Risks

### Source: Risks

- If scope keys use full arrangement/content hashes, every changed grouping or
  seating plan becomes a separate current-link lane instead of advancing the
  class current link.
- If scope keys stay account/browser-global, sharing Class A can hide or
  supersede the visible current link for Class B.
- If authenticated re-share revokes older links automatically, teachers may
  break links already posted in Teams, Google Classroom, or an LMS.
- If current-link state is stored only on artifacts, moving the current link
  risks mutating immutable artifact semantics and makes scope-version migration
  harder.
- If public guest mode gains discovery/import semantics, it will break the
  accepted public boundary and become difficult to explain or secure.
- If classroom-aware seating is not planned now, later import/discovery may be
  forced into a breaking schema change when rooms become shared assets.
- If organization/domain membership is treated too casually, teacher-to-teacher
  discovery could leak student names or classroom layouts across the wrong
  boundary.

## Notes

No additional current notes were recorded in the source.

## Decision And Assumption Ledger

The source does not record a separate decision and assumption ledger.

## Plan Document Review

The source does not include a plan document review record.

## Epic Closeout Review

The source does not include an epic closeout review record.
