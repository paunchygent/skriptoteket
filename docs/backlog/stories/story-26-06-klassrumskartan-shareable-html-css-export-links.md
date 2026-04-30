---
type: story
id: ST-26-06
title: "Klassrumskartan shareable HTML/CSS export links"
status: ready
owners: "agents"
created: 2026-04-30
updated: 2026-04-30
epic: "EPIC-26"
dependencies:
  - "ADR-0075"
  - "ADR-0079"
  - "ADR-0080"
  - "ADR-0084"
  - "ST-32-06"
acceptance_criteria:
  - "Given a teacher or guest has a current grouping or seating draft, when they open the existing export menu, then `Dela länk` is available as an export action beside PDF/Excel rather than as a separate workflow."
  - "Given `Dela länk` is triggered, when pending draft or smart-rule changes exist, then the same export-preparation persistence contract as PDF/Excel runs before the share artifact is created."
  - "Given a share link is created, when anyone opens the link without signing in, then they see an immutable responsive HTML/CSS presentation of the grouping or seating plan without editor controls, owner-scoped identifiers, app APIs, or live draft state."
  - "Given the share page may be posted in Microsoft Teams, Google Classroom, or an LMS forum, when the URL is previewed or opened, then the page has stable title/description metadata, readable responsive layout, and print-friendly CSS."
  - "Given an authenticated teacher creates a share link, when the artifact is stored, then it is durable, owned by that teacher, listable, copyable, and revocable without default expiry."
  - "Given a public guest creates a share link, when the public helper accepts the browser-owned snapshot, then it creates a public artifact with an expiry no later than 60 days and no owner-scoped persistence or authenticated API fallthrough."
  - "Given a public guest creates a newer share link for the same guest grouping or seating draft, when the browser still holds the previous revoke secret, then the previous guest share is revoked or superseded so the newest link is the active shared version."
  - "Given a share URL contains a readable slug, when the slug is missing or stale, then the unguessable token still resolves the artifact and the slug is never used as authorization."
  - "Given share pages may contain class, room, group, or student display names, when the route renders metadata or crawler responses, then it is excluded from sitemap coverage, uses `noindex,nofollow`, escapes all preview metadata, and defines cache behavior for active, revoked, expired, and missing-token responses."
  - "Given public guest share persistence is governed by the accepted `ADR-0084` exception, when the public guest slice is implemented, then it follows the accepted renderer-provenance, TTL-ceiling, creation-route, read-route, purge, and no-upgrade-import constraints."
ui_impact: "Adds `Dela länk` to authenticated and public Klassrumskartan export menus plus copy/revoke affordances."
data_impact: "Adds immutable shared classroom export artifacts with token-hash lookup, optional owner, expiry/revocation, and frozen HTML/CSS content."
---

## Context

Klassrumskartan can already export grouping and seating plans as PDF/Excel, but
teachers also need a URL they can post in Microsoft Teams, Google Classroom, or
an LMS forum wall. The URL should show a polished digital representation of the
same plan without requiring login, downloading a file, or exposing editor state.

This is a sharing/publishing feature, not live collaboration. The shared page
must behave like an exported artifact: it freezes the plan at the moment of
sharing.

## Notes

- `Dela länk` belongs in the existing export menu.
- The generated share view must reuse canonical export/presentation contracts
  rather than accepting browser-supplied HTML, CSS, or preview metadata.
- The public read route should be anonymous and token-based, for example
  `/share/classroom/{token}/{slug?}`.
- Public guest creation must stay on dedicated public helper creation routes;
  anonymous token reads are a separate public share route and must not fall back
  into SPA shell or account-owned APIs.
- The token is the authority and must be unguessable; store only a hash
  server-side.
- The slug is cosmetic and exists for link previews/readability only.
- Authenticated shares are teacher-owned and revocable.
- Guest shares are public-helper artifacts with abuse controls, a 60-day maximum
  TTL, and best-effort browser-held revoke/supersede behavior.
- Share artifacts must be immutable. Editing the draft later does not change an
  existing shared link.
- Sharing must not weaken the authenticated/public boundary from `ADR-0079`.
- Public guest share persistence is authorized only by the accepted `ADR-0084`
  exception. Outside that exception, the accepted `ADR-0079` rule still allows
  guest direct-download export only through browser-owned state, stateless
  helper work, direct rendering, and transient buffers.
- Share pages must follow a privacy-first crawler contract:
  - `noindex,nofollow`
  - no sitemap entry
  - no search-indexable canonical URL beyond the exact token URL needed for
    preview consistency
  - escaped Open Graph/Twitter-style metadata from sanitized presentation fields
  - explicit cache behavior for active, revoked, expired, missing-token, and
    stale-slug responses
- `Dela länk` must follow the export-preparation rule already required for
  PDF/Excel:
  - flush pending draft changes
  - flush pending smart-rule changes when relevant
  - validate `expected_revision`
  - render from canonical persisted draft/snapshot state
  - create share metadata only after successful render
  - dedupe or replace according to the authenticated/guest boundary rules
  - never fall back from public helper routes into authenticated owner-scoped
    APIs
- Planned PR slices:
  - `PR-0274` for authenticated share links, renderer, storage, read route,
    export-menu action, copy-link UX, list/revoke, lifecycle semantics, and
    expected-revision proof.
  - `PR-0273` for public guest share links under accepted `ADR-0084` authority,
    60-day TTL ceiling, public helper limits, snapshot revision guard, and
    browser-stored revoke/replace behavior.
