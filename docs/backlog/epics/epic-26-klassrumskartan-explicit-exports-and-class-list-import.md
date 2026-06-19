---
type: epic
id: EPIC-26
title: "Klassrumskartan — explicit exports and class-list import"
status: active
owners: "agents"
created: 2026-03-24
updated: 2026-06-18
outcome: "Teachers can export Klassrumskartan seating plans as a poster-grade standalone PDF, import class lists from common teacher files with confirmation before save, export seating as editable XLSX, export grouping first as an editable XLSX collaboration artifact and then as an A4 portrait PDF presentation artifact, publish immutable shareable HTML/CSS export links for grouping and seating with reliable renderer-derived Teams/social previews, and rely on teacher-facing planner surfaces that remain usable and hierarchy-stable while hosting those explicit I/O controls."
dependencies: ["ADR-0069", "ADR-0071", "ADR-0072", "ADR-0075", "EPIC-24"]
---

## Scope

- Introduce explicit teacher-facing export artifacts as the next Klassrumskartan lane after EPIC-24.
- Keep exports separate from autosave, draft continuity, and bounded undo/redo history.
- Ship seating exports before grouping exports.
- Treat the seating PDF as a standalone print renderer, not as a print stylesheet over the live planner UI.
- Keep Klassrumskartan-owned export artifacts local to Skriptoteket and use Sir Convert-a-Lot only
  for external/general-purpose conversion workloads where that keeps boundaries clear.
- Start with one seating PDF layout:
  - `pretty_brutalist_poster`
- Make the export contract layout-ready from the start so later stories can add teacher-selectable layouts without rewriting the renderer contract.
- Keep the seating PDF artifact focused on one-page whiteboard-friendly readability:
  - strong room geometry
  - large, legible student names
  - light branding only
  - no low-value metadata clutter
- Add bounded class-list import as the same teacher I/O lane:
  - `XLSX` as the primary structured import
  - `TXT` as a lightweight fallback
  - `PDF` parsed through Sir Convert-a-Lot using the fast parsing lane rather than the heavier default path
- Require teacher preview and confirmation before imported students or class names are saved.
- Prefer Hule internal-network service routing for Sir Convert-a-Lot in planning and implementation where available, with public/external access treated as a fallback rather than the primary lane.
- Follow seating exports with editable seating `XLSX`.
- Make grouping `XLSX` the first grouping export artifact because teachers often need to swap students, reorder members, and do final cleanup after export.
- Follow grouping `XLSX` with a separate grouping `PDF` presentation artifact.
- Treat grouping exports as their own artifact family rather than as seating exports with renamed labels:
  - grouping `XLSX` is the editable collaboration artifact
  - grouping `PDF` is the presentation/share artifact
- Default the grouping `PDF` lane to `A4` portrait and optimize it first for Teams / Google Classroom style digital sharing rather than for wall-poster display.
- Treat `Dela länk` as an export variant beside PDF/Excel rather than a separate sharing workflow.
- Require share links to use the same pre-export persistence contract as PDF/Excel:
  pending draft changes, relevant smart-rule changes, expected-revision
  validation, canonical saved snapshot rendering, and share metadata only after
  successful render.
- Make share pages immutable public HTML/CSS presentation artifacts with
  token-hash lookup, cosmetic slugs, responsive/print CSS, and sane link-preview
  metadata.
- Add renderer-derived preview thumbnails for share links so Microsoft Teams
  and similar link unfurlers can show the actual seating or grouping artifact
  while the opened URL remains the HTML/CSS share page.
- Keep public guest share persistence inside the accepted `ADR-0084` exception:
  dedicated public helper creation routes, anonymous token reads, 60-day expiry
  ceiling, renderer provenance, purgeability, and no automatic guest-upgrade
  import.

## Out of scope

- Reopening EPIC-24 for new feature work.
- Treating ordinary draft autosave or undo/redo state as teacher-facing export/checkpoint artifacts.
- Advanced teacher-facing checkpoint/history UX beyond the minimal explicit export contract.
- Student metadata expansion beyond what class-list import strictly needs to create or update a class roster.
- Zoning, smart placement, pair rules, weighting, or assignment intelligence.
- Finalizing unfinished teacher-note / smart-placement semantics under a generic UI-polish label.
- Reusing live planner CSS, DOM, or screenshots as the export implementation.
- Shipping multiple seating PDF layouts in the first export story.
- `DOCX` export in this epic unless a later approved story explicitly adds it.
- Executing the broader desktop-first planner redesign once that execution lane is owned by
  `EPIC-29`.
- Live draft sharing, collaborative editing, or exposing owner-scoped draft APIs
  through public share links.
- Using readable slugs as authority for share lookup or authorization.

## Risks

- A weak export renderer contract could accidentally couple artifact quality to current SPA layout constraints.
- PDF import could become over-scoped if it tries to perfectly understand arbitrary school documents instead of staying preview-first and teacher-confirmed.
- Grouping exports could drift into seating-first assumptions if the artifact models are not kept separate.
- Grouping XLSX could collapse into a backend-shaped dump unless workbook shape, headings, and page setup are specified before implementation starts.
- Share links could accidentally become live draft links unless artifacts freeze
  canonical saved state and public reads avoid app APIs.
- Public guest share creation could weaken `ADR-0079` unless it stays inside a
  cookie-agnostic public helper namespace with explicit TTL and abuse controls.
- Link-preview thumbnails could drift from the share artifact or leak stale
  student/class data unless they are generated from the immutable renderer and
  follow the same revocation, expiry, purge, and noindex boundaries as share
  HTML/CSS.

## Stories

- [x] [ST-26-01: Seating PDF poster export with standalone renderer](../stories/story-26-01-klassrumskartan-seating-pdf-poster-export-with-standalone-renderer.md)
- [ ] [ST-26-02: Class-list import from file with teacher preview and confirmation](../stories/story-26-02-klassrumskartan-class-list-import-from-file-with-preview-and-confirmation.md)
- [x] [ST-26-03: Seating XLSX export](../stories/story-26-03-klassrumskartan-seating-xlsx-export.md)
- [ ] [ST-26-04: Grouping PDF export](../stories/story-26-04-klassrumskartan-grouping-pdf-export.md)
- [x] [ST-26-05: Grouping XLSX export](../stories/story-26-05-klassrumskartan-grouping-xlsx-export.md)
- [ ] [ST-26-06: Klassrumskartan shareable HTML/CSS export links](../stories/story-26-06-klassrumskartan-shareable-html-css-export-links.md) — `PR-0276` static share-renderer and share-chrome/PDF remediation is approved after fixing merged-bench label overlay, wall-fixture geometry, owned chrome finalization, and relative public-app attribution proof gaps; `PR-0279` is closed and deployed after fixing shared-link seating label typography, long-name fit, and active seating preview backfill refresh semantics; `PR-0282` is closed after `REV-PR-0282` approved the seating/grouping shared-link `Ladda ner PDF` busy remediation through a tiny public-share browser-handoff guard plus canonical disabled/busy styling and duplicate-activation suppression, without Vue hydration, token logging, API calls, or share/PDF semantic changes; `PR-0303` is done and remediates public guest overview `Dela och exportera` state wiring without widening the accepted public guest share boundary.
- [ ] [ST-26-07: Klassrumskartan share-link Teams preview thumbnails](../stories/story-26-07-klassrumskartan-share-link-teams-preview-thumbnails.md) — `PR-0277` is implemented and deployed to Hemma production with renderer-derived preview assets, active-only metadata routes, production backfill, and BuildKit Chromium smoke; `PR-0279` production backfill rerun confirmed no stale active seating preview rows remained after the seating renderer refresh; `PR-0353` is ready to remediate the production Playwright browser-install `DEP0169` warning without dropping the thumbnail runtime; retained post-implementation review and fresh Teams unfurl proof remain before closeout.
- [ ] [ST-26-08: Klassrumskartan shared print PDF visual parity](../stories/story-26-08-klassrumskartan-shared-print-pdf-visual-parity.md) — `PR-0278` is ready for pre-implementation review and governs the PDF body redesign across workspace `Exportera PDF` and shared-link `Ladda ner PDF` for both seating and grouping.

## Implementation Summary (as of 2026-03-26)

- `ST-26-01` is implemented through `PR-0118`, `PR-0119`, `PR-0120`,
  `PR-0121`, `PR-0122`, `PR-0123`, `PR-0124`, `PR-0125`, and `PR-0146`.
- `ST-26-03` is implemented through `PR-0142` and `PR-0143`.
- `ST-26-05` is implemented through `PR-0139` and `PR-0140`.
- Seating exports now have an explicit prepare-contract seam plus a fully local
  PDF/XLSX artifact boundary inside Skriptoteket:
  standalone poster-scene translation, export-owned HTML/CSS rendering, local
  PDF/XLSX finalization, Vault persistence, typed status/download routes, and
  draft-scoped recovery without seating-specific Sir Convert callback/webhook
  orchestration.
- `ADR-0075` is now reflected in the shipped seating export lane, so
  Klassrumskartan-owned PDFs match the already-local grouping PDF/XLSX and
  seating XLSX artifact boundaries.
- Seating exports now also include a local `XLSX` lane that keeps `Affisch (A3)`
  as the default teacher action, exposes `Excel (.xlsx)` as a secondary option,
  and delivers a single-sheet `Sittplacering` workbook that preserves the room
  as a spatial seat grid with explicit empty seats, aisle gaps, and unplaced
  students.
- Grouping exports now include a local default `XLSX` lane that presents a
  protected `Redigera grupper` sheet with a student reassignment table, a
  separate `Gruppregister` order table, dropdown-guided small edits, and a
  formula-linked `Dela och exportera` sheet that stays presentation-ready in
  `A4` portrait.
- `ST-26-06` adds the next governed export variant: immutable shareable
  HTML/CSS links for grouping and seating, with authenticated durable shares
  first (`PR-0274`) and public guest shares with 60-day TTL and browser-held
  supersede/revoke behavior second (`PR-0273`). The 2026-04-30 UI assessment
  added two follow-up slices: `PR-0275` replaces detached share panels with
  the approved popover/bottom-sheet management pattern, and `PR-0276` replaces
  the seating share row/place directory with a real spatial classroom-map page.
  `REV-PR-0276` reopened and approved the spatial share renderer after fixing
  the merged bench label overlay and wall-fixture geometry fallback in the
  static share page, then refreshing renderer tests plus desktop/mobile visual
  proof. The follow-up share chrome/PDF addendum adds `Skapad: YYYY-MM-DD`,
  PDF download, and public-app attribution links to share pages; PDF downloads
  reuse the export-owned seating A3 poster renderer and grouping A4 PDF renderer
  from immutable share `presentation_payload` rather than printing the
  responsive share page. The share chrome follow-up now finalizes only owned
  date/PDF slots and uses a relative public-app attribution path, so placeholder
  sentinel text in user content is preserved and dev/staging share pages do not
  point at production. The 2026-05-01 Teams
  diagnostic proved that a share page with complete
  Open Graph/Twitter/schema.org metadata and a renderer-derived 1200x630
  `og:image` thumbnail unfurls with the expected seating arrangement in
  Microsoft Teams; `ST-26-07`/`PR-0277` turns that proof into the supported
  behavior for all active grouping and seating share links. The lane must
  preserve the accepted renderer-provenance, 60-day TTL ceiling, public
  create/read route split, purge, abuse-control, and no-upgrade-import
  constraints. `PR-0277` now stores 1200x630 PNG preview assets in PostgreSQL,
  generates them from finalized share HTML/CSS through a bounded Playwright
  adapter, exposes active-only token-addressed preview images, and emits
  escaped OG/Twitter plus allowlisted `CreativeWork` JSON-LD metadata. The
  production-like BuildKit Chromium smoke now proves the web image can install
  and launch Playwright Chromium for a 1200x630 render. Hemma production deploy
  at `2bae81a615a169aa70e916695cfaf467f5dbc96a` ran the dedicated
  share-preview deploy command, applied the preview-asset migration, backfilled
  3 active preview assets, passed the on-host Playwright PNG smoke, and proved
  the current production share URL exposes OG/Twitter/JSON-LD plus a 1200x630
  PNG preview route. The story remains open until retained post-implementation
  review and a never-before-posted Teams unfurl proof are recorded. A
  2026-06-14 Hemma production build warning investigation created `PR-0353` to
  upgrade or isolate the Playwright browser runtime so Node `DEP0169` warnings
  from Playwright's browser downloader do not remain in production build logs.
  `PR-0359` reviewed `PR-0277` for stale-state repair on 2026-06-18 and left it
  open intentionally: the implementation shipped, but the retained
  post-implementation review `REV-PR-0277` and the never-before-posted Teams
  unfurl proof are still outstanding, so `ST-26-07` remains active.
  `PR-0279` closed the linked static seating share-label correction: it keeps the opened
  share page as HTML/CSS, removes first/second-line label collision, handles
  ordinary long names without default ellipsis, and deployed the
  renderer-version/backfill refresh path for persisted seating preview PNGs.
- `ST-26-08` is the follow-up visual parity lane for the actual downloaded PDF
  artifacts. It keeps share-link PDF downloads export-backed and
  `presentation_payload`-derived, but redesigns the print-owned grouping and
  seating PDF bodies so workspace exports and share-link downloads inherit from
  the approved shared-link renders without adding web action chrome to the PDFs.
- The `PR-0122` Hemma deploy gate is now production-proven through the on-host
  callback-capable export smoke and Vault-backed download, while `PR-0125`
  now extends that operator flow with review-fixed canonical replacement,
  fail-closed canonical-only validation, saved webhook inventories, and a
  successful rerun of the Hemma deploy/readiness gate for the revised build.
- Adjacent desktop UI-hardening ideas that surfaced during export/import planning were later
  consolidated into `EPIC-29`, which is now the canonical overhaul hub.

## Notes

- This epic follows the accepted EPIC-24 direction that durable artifacts come later through explicit export rather than ordinary save.
- The first shipped export artifact is intentionally “no slop”:
  - one page
  - poster-grade
  - readable at distance
  - no second-page filler
- Editable/tabular needs belong to `XLSX`, not to extra PDF pages.
- For seating, `PDF` remains the default export action:
  - `XLSX` joins the same export menu as a secondary operational artifact
  - the workbook is generated locally rather than through Sir Convert-a-Lot
- For grouping, editable/tabular needs come first:
  - `XLSX` is the primary teacher workflow artifact
  - `PDF` follows as the cleaner presentation/share artifact
- Grouping `PDF` should read like a digital handout:
  - `A4` portrait by default
  - easy to post in Teams or Google Classroom
  - printable when needed, but not designed as a classroom wall poster
- Shareable links should read like public presentation pages:
  - responsive for phone, tablet, desktop, and projector
  - readable without login, JavaScript, or app chrome
  - printable through good `@media print`
  - equipped with OpenGraph/Twitter-style metadata
  - clear about whether the artifact is a grouping or seating plan
- PDF import should use the existing Sir Convert-a-Lot service model rather than introducing a bespoke heavy parsing lane inside Klassrumskartan itself.
- For Klassrumskartan-owned artifacts, export rendering/runtime stays planner-owned inside
  Skriptoteket per `ADR-0075`.
- Sir Convert-a-Lot remains the preferred dedicated service boundary for external/general-purpose
  conversion and PDF extraction rather than for Klassrumskartan's final teacher-facing PDF
  artifacts.
- A review doc should be created and approved before implementation begins, per the repo review workflow.
