---
type: story
id: ST-SKRIPT-26-06
title: Klassrumskartan shareable HTML/CSS export links
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: ready
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
epic: EPIC-SKRIPT-26
acceptance_criteria:
- Given a teacher or guest has a current grouping or seating draft, when they open
  the existing export menu, then `Dela länk` is available as an export action beside
  PDF/Excel rather than as a separate workflow.
- Given `Dela länk` is triggered, when pending draft or smart-rule changes exist,
  then the same export-preparation persistence contract as PDF/Excel runs before the
  share artifact is created.
- Given a share link is created, when anyone opens the link without signing in, then
  they see an immutable responsive HTML/CSS presentation of the grouping or seating
  plan without editor controls, owner-scoped identifiers, app APIs, or live draft
  state.
- Given the share page may be posted in Microsoft Teams, Google Classroom, or an LMS
  forum, when the URL is previewed or opened, then the page has stable title/description
  metadata, readable responsive layout, and print-friendly CSS.
- Given an authenticated teacher creates a share link, when the artifact is stored,
  then it is durable, owned by that teacher, listable, copyable, and revocable without
  default expiry.
- Given a public guest creates a share link, when the public helper accepts the browser-owned
  snapshot, then it creates a public artifact with an expiry no later than 60 days
  and no owner-scoped persistence or authenticated API fallthrough.
- Given a public guest creates a newer share link for the same guest grouping or seating
  draft, when the browser still holds the previous revoke secret, then the previous
  guest share is revoked or superseded so the newest link is the active shared version.
- Given a share URL contains a readable slug, when the slug is missing or stale, then
  the unguessable token still resolves the artifact and the slug is never used as
  authorization.
- Given share pages may contain class, room, group, or student display names, when
  the route renders metadata or crawler responses, then it is excluded from sitemap
  coverage, uses `noindex,nofollow`, escapes all preview metadata, and defines cache
  behavior for active, revoked, expired, and missing-token responses.
- Given public guest share persistence is governed by the accepted `ADR-SKRIPT-0084`
  exception, when the public guest slice is implemented, then it follows the accepted
  renderer-provenance, TTL-ceiling, creation-route, read-route, purge, and no-upgrade-import
  constraints.
retired_ids:
- ST-26-06
---

## Context

### Source: Context

Klassrumskartan can already export grouping and seating plans as PDF/Excel, but
teachers also need a URL they can post in Microsoft Teams, Google Classroom, or
an LMS forum wall. The URL should show a polished digital representation of the
same plan without requiring login, downloading a file, or exposing editor state.

This is a sharing/publishing feature, not live collaboration. The shared page
must behave like an exported artifact: it freezes the plan at the moment of
sharing.

## Epic Contract Slice

The source does not provide a separate epic contract slice section; no additional epic contract slice is recorded.

## ADR Coverage

The source does not provide a separate adr coverage section; no additional adr coverage is recorded.

## Contract Inputs

The source does not provide a separate contract inputs section; no additional contract inputs is recorded.

## Live Verification Plan

The source does not provide a separate live verification plan section; no additional live verification plan is recorded.

## Non-Goals

The source does not provide a separate non-goals section; no additional non-goals is recorded.

## Notes

### Source: Notes

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
  - `PR-0275` for replacing detached owned-share panels with the approved
    desktop popover and mobile bottom-sheet management pattern.
  - `PR-0276` for replacing the seating share row/place directory with a real
    spatial classroom-map share page and polishing grouping share cards.
  - `PR-0279` for fixing shared-link seating seat-label typography so ordinary
    long names render without default ellipsis, first/second-line labels do not
    collide, and renderer-derived preview assets stay lifecycle-safe after the
    static share renderer changes.
- Follow-up story:
  - `ST-26-07` / `PR-0277` for turning the 2026-05-01 production Teams
    diagnostic into supported renderer-derived `og:image` thumbnails and full
    link-preview metadata for all active grouping and seating share links.
  - `ST-26-08` / `PR-0278` for redesigning the actual downloaded PDFs across
    workspace `Exportera PDF` and shared-link `Ladda ner PDF`, keeping share
    PDFs export-backed and `presentation_payload`-derived while borrowing the
    approved shared-link body language.
  - `PR-0279` remains a shared-link HTML/CSS renderer correction rather than a
    PDF visual-redesign slice. It is linked to `ST-26-07` because Teams/social
    preview PNGs are generated from the same immutable seating share artifact.
    `REV-PR-0279` was re-reviewed and approved on 2026-05-03, then deployed to
    Hemma as `b7bc5d9d`. The deploy log
    `/home/paunchygent/apps/skriptoteket/.artifacts/hemma-deploy-20260503-121524.log`
    shows web/worker rebuild, migrations, and local seating export smoke passed.
    The production backfill command returned `scanned=0 generated=0 refreshed=0
    failed=0`, confirming no active stale seating preview rows remained after
    deploy, and production health returned healthy.
  - `PR-0282` is closed after `REV-PR-0282` re-review approved the shared-link
    `Ladda ner PDF` busy lifecycle remediation. The implemented slice aligns
    spinner geometry with the `UiDenseSpinner` language from `PR-0281`,
    suppresses duplicate activation while busy, and keeps the share PDF action
    chrome in a dedicated SRP helper module. The controller now uses a short
    browser-handoff guard that clears busy state without waiting for
    focus/visibility recovery, and retained browser proof asserts idle
    recovery, restored `href`, cleared busy attributes, duplicate suppression,
    and stable geometry.
  - `PR-0286` is closed as a cross-linked `ST-29-11` toolbar composition slice:
    it moves file export choices into the workspace `Dela` affordance as
    `Dela och exportera` while preserving this story's share-artifact,
    export-preparation, and link-management contracts.
  - `PR-0301` is closed as a cross-linked `ST-29-11` overview-selector polish
    slice: it may change the visible `Välj innehåll` selector and selected-draft
    confirmation inside `Dela och exportera`, but it did not change this
    story's share-artifact, export-preparation, link-management, revoke, or
    public-read contracts.
  - `PR-0303` is done as a public guest remediation slice for the overview
    `Dela och exportera` state wiring defect: the public overview now prepares
    the selected browser-owned draft before share/export, passes public
    share/export state into the overview panel, shows workspace-created links in
    the matching created-links section, and hydrates browser-held current-link
    metadata after the relevant draft/snapshot becomes available.
  - `PR-0307` is ready as the authenticated share-as-export Smart-history
    provenance slice: owner-scoped `Dela` should create the same eligible
    grouping/seating checkpoint history as PDF/Excel exports, while public guest
    shares remain excluded from account-backed history.
- Closed remediation:
  - `REV-PR-0276` found that the shipped static seating share page breaks the
    merged-bench label contract: the export model merges bench geometry, but
    `share_scene_renderer.py` lays the bench bar and `Bänk` label out as flex
    siblings, so the label is pushed to the right instead of centered over the
    full merged span.
  - Remediation stayed inside `PR-0276` because that slice owns the static
    share-page HTML/CSS renderer and its desktop/mobile visual proof. The fix
    now positions the bench body and label as absolute overlay elements, adds a
    renderer test for a normalized merged `Bänk` fixture, and refreshes
    desktop/mobile visual artifacts with that fixture visible.
  - A second `PR-0276` renderer defect found that `placement=WALL` fixtures
    without `wall_side` silently rendered as floor tiles. The renderer now
    fails closed for invalid wall fixtures, tests a valid top whiteboard above
    the floor band, and refreshes visual proof with `wall_side=TOP`.
- Reopened `PR-0276` follow-up:
  - Share-page headers for both seating and grouping must show `Skapad:
    YYYY-MM-DD`, add a PDF download action in the top-right header area, and
    add the `Skapad av Klassrumskartan` public-app attribution link. Seating
    pages must no longer show `Delad sittschema - endast för visning.`.
  - The PDF action must render immutable seating shares as a single A3
    landscape page that maximizes classroom-map space, and immutable grouping
    shares as A4 portrait, with screen-only actions omitted from print. PDF
    attachment filenames must include the share slug and artifact creation date
    as `YYYY-MM-DD`.
  - Share PDF downloads are rendered from the stored canonical
    `presentation_payload` through the existing seating/grouping export PDF
    renderers, not by printing the responsive public share page. Repeated clicks
    in one backend process reuse a bounded in-process cache for the same
    immutable artifact.
  - The follow-up review also closed two share-chrome defects: date/PDF
    finalization now targets explicit renderer-owned chrome slots so escaped
    user content containing placeholder sentinel strings is preserved, and the
    `Skapad av Klassrumskartan` attribution now uses the same-origin public app
    path instead of a hard-coded production URL.
- Approved share UI and share-page visual direction lives in
  `docs/mockups/st-26-06-share-link-ux-and-page-renderer/`.

## Decision And Assumption Ledger

The source does not provide a separate decision and assumption ledger section; no additional decision and assumption ledger is recorded.

## Plan Document Review

The source does not provide a separate plan document review section; no additional plan document review is recorded.

## Story Closeout Review

The source does not provide a separate story closeout review section; no additional story closeout review is recorded.
