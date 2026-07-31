---
type: epic
id: EPIC-SKRIPT-37
title: Backlog product-direction inventory and app surface realignment
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: active
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
outcome: Skriptoteket has a truthful active backlog that preserves still-valuable
  script/editor work, closes completed or superseded legacy tasks, and sequences the
  next UI shell and app-presentation work around current teacher-facing product lanes.
retired_ids:
- EPIC-37
---

## Scope

### EPIC-37: Backlog Product-Direction Inventory And App Surface Realignment

### Scope

- Inventory active/proposed/ready/in-progress/blocked epics, stories, and PR
  backlog tasks against current product direction and current code reality.
- Repair stale backlog state by marking completed items `done`, obsolete stories
  or PR tasks `canceled`, and invalid epics `dropped` with retained rationale.
- Preserve still-valuable script creation, editor, runner, governance, and
  tool-authoring work when it remains aligned with the current architecture,
  even though bespoke apps are now the main product proposition.
- Freeze the current product-lane framing before new shell work:
  `Klassrumskartan`, audio transcription, Exam Converter, and general document
  conversion.
- Clarify the Sir Convert-a-Lot boundary so heavy conversion/model/runtime work
  stays producer-owned while native Skriptoteket app state stays product-owned.
- Re-enter the service shell/dashboard redesign only after stale backlog state
  is inventoried, so UI work does not build on a misleading product map.
- Plan app presentation decomposition so generic Conversion Hub framing can be
  replaced by use-case-specific app entries, names, descriptions, and routes
  where the reviewed product direction calls for it.

### Out Of Scope

- Production UI or API implementation before this proposed package is reviewed.
- Deleting historical backlog records merely because they are old.
- Scrapping the script editor, runner, or script-governance work solely because
  bespoke apps have become the front-door value proposition.
- Moving lightweight native exam, transcript, or app-state editing back into Sir
  Convert-a-Lot replay/hash/fingerprint workflows when no heavy conversion
  boundary is required.

### Story Stack

- [ST-37-01: Backlog inventory and stale-state repair](../stories/story-37-01-backlog-inventory-and-stale-state-repair.md)
- [ST-37-02: Current product lane and Sir Convert boundary reset](../stories/story-37-02-current-product-lane-and-sir-convert-boundary-reset.md)
- [ST-37-03: Service shell and dashboard UX realignment](../stories/story-37-03-service-shell-and-dashboard-ux-realignment.md)
- [ST-37-04: App presentation decomposition and naming reset](../stories/story-37-04-app-presentation-decomposition-and-naming-reset.md)
- [ST-37-05: Cross-app save/export file naming protocol](../stories/story-37-05-cross-app-save-export-file-naming-protocol.md)

### Risks

- If the inventory becomes a mass cancelation pass, valuable script/editor work
  may be lost instead of preserved under the right product framing.
- If UI redesign starts before stale backlog cleanup, the dashboard may inherit
  old "generic tool catalog" or "generic conversion hub" assumptions.
- If Sir Convert-a-Lot remains the default owner for simple app-state edits,
  workflows will keep unnecessary replay, fingerprint, and artifact-overlay
  complexity.
- If generic app presentation is left untouched, teachers will not see the
  product as a set of clear productivity applications.

### Dependencies

- Product-direction reference:
  [REF-current-product-direction-and-backlog-inventory-2026-06-17](../../reference/ref-current-product-direction-and-backlog-inventory-2026-06-17.md)
- Current product lanes and Sir Convert boundary:
  [REF-current-product-lanes-and-sir-convert-boundary-v1](../../reference/ref-current-product-lanes-and-sir-convert-boundary-v1.md)
- Retained review workflow:
  [REF-review-workflow](../../reference/ref-review-workflow.md)
- Existing script/editor and SPA foundations:
  [EPIC-11](epic-11-full-vue-spa-migration.md),
  [EPIC-14](epic-14-admin-tool-authoring.md),
  [EPIC-16](epic-16-catalog-discovery-and-personalization.md)
- Current bespoke app lanes:
  [EPIC-21](epic-21-curated-app-conversion-hub.md),
  [EPIC-29](epic-29-klassrumskartan-desktop-first-workspace-overhaul.md)

### Review Gate

`REV-EPIC-37` approved this package on 2026-06-18. `PR-0361` closed the
service-shell UX planning package, and `PR-0362` closed the app-presentation
naming package. The remaining epic work is implementation through `PR-0363`
onward plus the ST-37-04 follow-up slices.

### Implementation Summary

- `PR-0358` is done: the retained inventory artifact
  [REF-pr-0358-active-backlog-inventory-2026-06-17](../../reference/ref-pr-0358-active-backlog-inventory-2026-06-17.md)
  classifies 196 open backlog rows and defines the recommended first cleanup
  queue for `PR-0359`.
- `ST-37-01` is done as of 2026-06-18: `PR-0359` applied the first reviewed
  docs-only stale-state repair and supersession cleanup batch, approved by
  [REV-PR-0359](../reviews/review-pr-0359-stale-state-repair-and-supersession-cleanup-batch.md).
  The remaining epic work is the product-lane/boundary reference, service-shell
  UX realignment, and app-presentation decomposition.
- `ST-37-02` is done as of 2026-06-18: `PR-0360` added
  [REF-current-product-lanes-and-sir-convert-boundary-v1](../../reference/ref-current-product-lanes-and-sir-convert-boundary-v1.md)
  as the durable product-lane and Sir Convert/Skriptoteket ownership doctrine.
  The remaining epic work is service-shell UX realignment and app-presentation
  decomposition after the approved epic review gate.
- `PR-0361` is done as of 2026-06-18. It added
  [REF-service-shell-ux-realignment-plan-v1](../../reference/ref-service-shell-ux-realignment-plan-v1.md)
  and the route-visible implementation sequence `PR-0363` through `PR-0365`
  for conversion-lane deep links, authenticated home app-lane hierarchy, and
  authenticated shell navigation.
- `PR-0362` is done as of 2026-06-18. It added
  [REF-app-presentation-decomposition-and-naming-plan-v1](../../reference/ref-app-presentation-decomposition-and-naming-plan-v1.md),
  which closes the planning baseline for lane names, descriptions, truthful
  entrypoints, proof gates, and follow-up sequencing for `Klassrumskartan`,
  `Audio Transcription`, `Exam Converter`, and future `Document Converter`.
  `ST-37-04` remains open for implementation through public-landing follow-up
  slices `PR-0370` through `PR-0372` and the remaining app-presentation slices
  `PR-0366` through `PR-0369`, the post-cutover cleanup slice `PR-0374`, and
  the separate Document Converter planning slice `PR-0375`,
  while `PR-0363` through `PR-0365` are now unblocked by planning and remain
  governed by their own review docs.
- `PR-0363` is done as of 2026-06-19. It added the now-retired authenticated
  `/apps/documents.conversion_hub?mode=exam|transcript` cutover bridge,
  kept app-id/route/registry/public/backend/Sir Convert/HuleEdu/QTI/DOCX
  surfaces unchanged, retained HuleEdu browser-session proof, and encoded the
  Docker-service breadcrumb for Gateway-backed proof.
- `PR-0364` is done and approved as of 2026-06-19. It implemented the
  authenticated home work-app surface with current runnable lanes first, no
  fake Document Converter route, and script/editor/platform surfaces preserved
  as secondary continuation.
- `PR-0365` is done as of 2026-06-19. It corrected the authenticated shell so
  authenticated home remains the owned app-entry surface, removed duplicate
  `Klassrumskartan`/`Provhantering`/`Ljudtranskribering`/`Kodredigerare` links
  from the persistent sidebar and mobile drawer, kept `Föreslå verktyg`
  visible to all signed-in users, kept role-gated links below the utility
  block while leaving `Hjälp` to the top auth bar, and retained truthful
  shared-auth browser proof under
  `.artifacts/playwright-pr-0365-authenticated-shell-navigation/20260619T212625Z/`.
- `ST-37-03` is now done as of 2026-06-19. The service-shell/dashboard
  realignment sequence is closed by `PR-0361`, `PR-0363`, `PR-0364`, and
  `PR-0365`, while the epic remains active for the remaining `ST-37-04`
  follow-up slices.
- `PR-0370` and `PR-0371` are done as of 2026-06-19. They approved and then
  implemented the public landing authenticated-app preview, removing the
  repeated signed-out Klassrumskartan showcase while preserving the hero-owned
  Klassrumskartan CTA.
- `PR-0372` is done as of 2026-06-19. It simplified the signed-out public
  header so the hero retains sole ownership of the `Klassrumskartan` CTA while
  the header keeps only the brand, `Logga in`, and `Hjälp` as same-style
  single-row actions on small screens, with retained in-app-browser desktop
  and mobile proof from `http://localhost:5173/`.
- `PR-0366` is done as of 2026-06-20. It aligned copy-only app-lane
  descriptions and labels across authenticated home, the authenticated
  prov/transcript mode switch, the authenticated compatibility host frame, and
  the public Exam Converter eyebrow without changing routes, app ids, registry
  metadata, or backend/API contracts.
- `PR-0373` is done as of 2026-06-20. It hardened the local public-app proof
  lane after `PR-0366` exposed a host Vite setup where public
  `/api/v1/public/...` traffic had no running Skriptoteket backend target:
  Docker web-only startup, host shared-auth Vite env, and Docker frontend
  public API proxy ownership are now explicit and covered by a focused contract
  test. `PR-0367`, `PR-0368`, and `PR-0374` have since closed the registry,
  route-visible identity split, and post-cutover compatibility cleanup.
- `PR-0375` is done and approved by `REV-PR-0375` as of 2026-06-23. It defines
  a real backend-backed Document Converter MVP under the scoped
  `documents.conversion_hub/document-converter` backend contract with a
  single-result artifact, server-authoritative download/save, retry/replay as
  new submission by default, and split backend/API versus route-visible proof
  obligations. The reserved backend/API alignment slice `PR-0369` remains
  blocked unless later route-visible work proves a concrete contract need.
- `PR-0380` is done as of 2026-06-23. It supersedes the one-file/Sir
  Convert-first Document Converter assumption for follow-up planning: simple
  conversion lanes should run inside the Skriptoteket app boundary, Sir Convert
  remains reserved for heavy/OCR/complex PDF paths, general batch input targets
  up to 10 items or project entries, and route-visible UI remains blocked
  behind the approved mockup and copy pipeline.
- `PR-0381` is done and approved by `REV-PR-0381` as of 2026-06-25. It keeps
  the Document Converter route inactive, adds the scoped batch contract,
  automatic local/heavy producer decisions, first local simple lanes, shared
  document rendering/extraction adapters, and server-owned local artifact
  authority. The next route-inactive product contract slice is `PR-0382`.
- `PR-0382` through `PR-0384` are done and approved: the HTML/CSS project
  preview contract exists, mockup/copy approval closed, and
  `/apps/document-converter` is route-visible. `PR-0387` closed small-screen
  mockup remediation, and `PR-0388` is done and approved by `REV-PR-0388`: the
  route now has automatic PDF preview, no implementation-detail state copy, and
  best-effort support for ordinary grid-heavy teacher HTML/CSS before
  files/history work proceeds.
- `ST-37-05` is now planned as a separate follow-up from `PR-0385`. It owns the
  cross-app save/export file naming protocol, editable filename stems,
  extension ownership, `Mina filer` rename behavior, and app-specific adoption
  sequence through `PR-0390` through `PR-0396`.

## Epic Contract

The source material below remains authoritative for this section.

## Contract Inputs

The source material below remains authoritative for this section.

## Stories

The source material below remains authoritative for this section.

## Epic Verification Plan

Verification expectations remain in the retained source material below.

## Exceptions And Follow-Ups

The source boundaries and recovery limits remain preserved below.

## Risks

The source material below remains authoritative for this section.

## Notes

The source material below remains authoritative for this section.

## Decision And Assumption Ledger

The source material below remains authoritative for this section.

## Plan Document Review

The source material below remains authoritative for this section.

## Epic Closeout Review

The source material below remains authoritative for this section.
