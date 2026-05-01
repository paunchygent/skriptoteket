---
type: reference
id: REF-klassrumskartan-scoped-sharing-and-import-direction-2026-05-01
title: "Klassrumskartan scoped sharing and import direction"
status: active
owners: "agents"
created: 2026-05-01
topic: "klassrumskartan-scoped-sharing-and-import"
links: ["EPIC-36", "EPIC-24", "EPIC-26", "EPIC-32", "ST-26-06"]
---

## Overview

Klassrumskartan sharing should follow the teacher's pedagogical object, not the
browser or account that happened to create the latest link.

The product direction is class-first:

- a class can have a current grouping share link
- the same class can have a separate current seating share link
- another class can have its own current grouping and seating links at the same
  time
- later, seating should be able to add classroom context so one reusable
  classroom can host different seating arrangements for different classes.

This reference records the target model before implementation slices change the
current share-link behavior.

Terminology decision:

- `roster_fingerprint` is the canonical scope term.
- It represents the portable class-list/content identity teachers experience as
  a class.
- It includes the roster name plus normalized student display-name membership.
  This is intentional because rosters may represent courses rather than formal
  classes, and one teacher can have several course rosters with identical
  students.
- Local student ids are account/browser-local row identities and must not be
  part of the portable scoped-sharing fingerprint.
- The docs should explain that meaning in prose rather than introduce
  `class_fingerprint` as a parallel term.
- This direction does not introduce a separate durable Class aggregate.

## Current Problem

The existing share-link implementation has two useful but incomplete scopes:

- Authenticated shares are owner and draft scoped. Listing/revoke behavior is
  tied to `owner_user_id + draft_id + draft_kind`.
- Public guest shares are browser and snapshot scoped. The browser stores the
  newest link metadata in local storage and the backend enforces limits against
  a full guest snapshot fingerprint.

Those scopes are safe for the first share-link release, but they are not the
long-term product model. A teacher thinking in Klassrumskartan terms expects
the current link to belong to the class's current grouping or seating work, not
to a global account/browser lane.

## Target Scope Key

Use a current-share scope key that identifies the semantic object whose newest
share link is being managed.

Near-term grouping:

```text
roster_fingerprint + draft_kind=grouping
```

Seating:

```text
roster_fingerprint + classroom_fingerprint + draft_kind=seating
```

Seating share creation requires a selected classroom/template. Seating drafts
may exist without room context in the workspace, but the share/export action
should be disabled or explain that the teacher must select a classroom before
creating a seating link.

Grouping may later include classroom context for smarter grouping, but grouping
must remain valid without a classroom. Classroom context should therefore not be
required for grouping scope.

Grouping share scope should always remain:

```text
roster_fingerprint + draft_kind=grouping
```

Classroom context may be part of the logic that leads to a grouping snapshot,
but it is not part of the presentational identity of the shared grouping
artifact.

## Classroom Fingerprint Semantics

`classroom_fingerprint` is the portable identity for classroom templates. It is
used for authenticated classroom-template import/discovery and seating share
scope.

Conceptually:

```text
classroom_fingerprint = hash(normalized_template_name, canonical_room_geometry)
```

It should be derived from:

- normalized room/template name
- grid dimensions
- seat positions and zones
- fixture types, positions, dimensions, and labels when labels are part of the
  teacher-facing room meaning.

Ordering must be canonicalized by geometry and teacher-facing properties where
possible. Local template ids, seat ids, and fixture ids are row/local-state
identities and must not affect the portable fingerprint unless a later reviewed
model gives those ids semantic meaning.

Fixture labels are identity-bearing when present because they are
teacher-facing room metadata. Normalize them with the same conservative profile
used for roster and template names; do not infer or alias label meanings.

## Roster Fingerprint Semantics

`roster_fingerprint` should be derived from normalized roster name plus
an order-insensitive sorted multiset of normalized student display names.
Duplicate display names must be preserved because duplicate names are a real
ambiguity, not something the fingerprint should silently collapse.

Conceptually:

```text
roster_fingerprint = hash(
  normalized_roster_name,
  sort(normalized_student_display_names_with_duplicates_preserved),
)
```

Normalization for this v1 fingerprint should stay conservative:

- trim leading/trailing whitespace
- collapse internal whitespace runs to one space
- Unicode-normalize to NFC
- case-fold for the hash input
- do not strip accents
- do not remove punctuation
- do not reorder names such as `Karlsson, Anna` into `Anna Karlsson`
- do not apply locale-specific nickname or name-matching logic.

This means `Anna Karlsson` and `anna karlsson` match after normalization, while
`José` and `Jose` remain distinct, and `Karlsson, Anna` remains distinct from
`Anna Karlsson`.

Apply the same normalization profile to roster names and student display names.
That keeps `Matematik 8A` and `matematik 8a` aligned while preserving meaningful
punctuation and accents in course labels such as `Sv/SO 8B`, `Ma-No`, or
`Français`.

Implementation should expose this as an injected fingerprinting policy/service,
not as repeated ad hoc helpers. The service should own:

- normalization profile version
- roster fingerprint payload construction
- stable sorting with duplicate preservation
- hash serialization format
- future migration path for school/organization student ids.

Application handlers, API routes, repositories, and frontend flows should call
that boundary rather than reimplement the algorithm locally.

## Fingerprint Authority

Authenticated scoped sharing should compute `roster_fingerprint` on the server.
The frontend should continue to pass stable route/action inputs such as
`draft_id` and `expected_revision`; the backend resolves the draft, loads the
roster, computes the fingerprint through the injected service, and persists or
uses that authoritative scope.

For public guest mode, browser-side fingerprints may remain useful for local UX
keys. They must not become persistence authority. Public helper endpoints should
recompute or validate any server-relevant roster/scope fingerprint from the
submitted snapshot before creating, superseding, revoking, or limiting persisted
share state.

The existing server-side guest-upgrade helper already hashes portable
teacher-facing roster content from roster name and student display names; future
authenticated scope-key work should preserve the semantic above unless a
reviewed migration changes the fingerprint version.

Roster name is identity-bearing, not decorative, because teachers may model
course groups rather than formal classes. Two courses can have the same students
and still need separate current share links.

Local student ids must not participate in this portable fingerprint. They are
row/local-state identities, so including them would prevent two teachers or two
browsers from recognizing the same roster content. A later authenticated
school/organization roster model may add stable student ids through an explicit
new fingerprint version, but that is not part of this direction yet.

## Artifact Identity Versus Scope Identity

Do not use the arrangement/content hash as the current-link scope key.

The scope key answers:

> Which teacher object should this current link represent?

The artifact identity answers:

> What immutable presentation snapshot did this URL publish?

Keep these concepts separate:

- `roster_fingerprint`: portable identity for the class roster/content.
- `classroom_fingerprint`: portable identity for a reusable classroom layout.
- `draft_kind`: grouping or seating.
- `presentation_hash` / `content_hash`: immutable artifact version proof.
- `public_token` hash: URL lookup authority.
- `revoke_secret` hash: public guest browser-owned revoke authority.
- current-share pointer: latest active artifact for the semantic scope.

If the arrangement hash becomes part of the current scope, every changed
grouping or seating plan becomes a new lane. That defeats the desired "current
link for this class" behavior.

For authenticated sharing, creating a newer share for the same scope should move
the current-share pointer only. It must not automatically revoke older
authenticated links because those links may already have been posted in Teams,
Google Classroom, an LMS, or a message thread. Older authenticated artifacts
remain token-addressable until the teacher explicitly revokes them or a lifecycle
rule revokes them.

Represent that current-share pointer as its own persistence model. Share
artifacts may store scope metadata for audit and query, but the mutable "current
link for this scope" state should live in a separate pointer row keyed
conceptually by:

```text
owner_user_id
+ scope_kind
+ scope_version
+ roster_fingerprint
+ optional classroom_fingerprint
+ draft_kind
```

The pointer row references `share_artifact_id`. Re-sharing atomically updates
the pointer to a newer immutable artifact while preserving older artifacts and
their token URLs.

Public guest sharing may keep narrower TTL-bound browser-owned supersede/revoke
behavior inside the accepted `ADR-0084` exception, because it is not the durable
teacher-to-teacher import/discovery model.

## Authenticated Direction

Authenticated sharing is the long-term coherent model for durable sharing,
discovery, and import.

Authenticated users should eventually be able to:

- share a current grouping or seating artifact scoped to a class
- keep different current links for different classes at the same time
- discover shared rosters and classroom templates when an approved
  organization/domain policy says they belong to the same context
- import or copy shared assets into their own account without mutating the
  source teacher's assets
- reuse the same classroom template with different class seating arrangements.

Organization or domain matching is a product direction, not a complete
authorization policy. A later story must define the accepted membership,
privacy, and audit contract before discovery is implemented.

## Public Guest Boundary

Public guest mode should remain deliberately smaller.

Public guest sharing may use class-scoped browser metadata so the same browser
can manage current links for multiple classes more coherently. It must not grow
into:

- public share discovery
- public import
- cross-browser guest sync
- public dashboards
- account-style listing APIs
- automatic guest-share migration into an account.

This keeps public sharing inside the accepted `ADR-0084` exception and avoids
making browser storage carry a product model it cannot safely own.

## Import Direction

Future import/discovery belongs to authenticated users and should focus on
reusable assets, not short-lived arrangement state.

The import model should be copy/import oriented:

- importing a class list creates or reuses an account-owned class roster
- importing a classroom creates or reuses an account-owned classroom template

Imports should be non-destructive by default. Exact fingerprint matches may
reuse existing assets; name collisions with different fingerprints should create
separate assets or require explicit teacher choice.

Grouping and seating snapshots should remain shareable/exported artifacts unless
a later reviewed product slice identifies real import value. They are mutated
often and are already useful as immutable shared links; importing them as drafts
risks adding complexity without saving much teacher time.

## Implementation Notes For Future Slices

- Add a reviewed current-share scope contract before changing persistence.
- Prefer additive schema fields for scope identity, then migrate existing
  share-artifact behavior deliberately.
- Keep immutable share URLs token-authoritative; readable slugs remain cosmetic.
- Keep current-link scope separate from share artifact storage so older links
  can remain available or be revoked according to lifecycle rules.
- Treat public guest class-scoped metadata as a UX coherence improvement only.
- Do not add discovery/import until authenticated organization policy is
  accepted.
