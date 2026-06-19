---
type: epic
id: EPIC-37
title: "Backlog product-direction inventory and app surface realignment"
status: active
owners: "agents"
created: 2026-06-17
updated: 2026-06-19
outcome: "Skriptoteket has a truthful active backlog that preserves still-valuable script/editor work, closes completed or superseded legacy tasks, and sequences the next UI shell and app-presentation work around current teacher-facing product lanes."
dependencies:
  - "REF-current-product-direction-and-backlog-inventory-2026-06-17"
  - "REF-current-product-lanes-and-sir-convert-boundary-v1"
  - "REF-service-shell-ux-realignment-plan-v1"
  - "REF-app-presentation-decomposition-and-naming-plan-v1"
  - "REF-review-workflow"
  - "EPIC-11"
  - "EPIC-14"
  - "EPIC-16"
  - "EPIC-21"
  - "EPIC-29"
---

# EPIC-37: Backlog Product-Direction Inventory And App Surface Realignment

## Scope

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

## Out Of Scope

- Production UI or API implementation before this proposed package is reviewed.
- Deleting historical backlog records merely because they are old.
- Scrapping the script editor, runner, or script-governance work solely because
  bespoke apps have become the front-door value proposition.
- Moving lightweight native exam, transcript, or app-state editing back into Sir
  Convert-a-Lot replay/hash/fingerprint workflows when no heavy conversion
  boundary is required.

## Story Stack

- [ST-37-01: Backlog inventory and stale-state repair](../stories/story-37-01-backlog-inventory-and-stale-state-repair.md)
- [ST-37-02: Current product lane and Sir Convert boundary reset](../stories/story-37-02-current-product-lane-and-sir-convert-boundary-reset.md)
- [ST-37-03: Service shell and dashboard UX realignment](../stories/story-37-03-service-shell-and-dashboard-ux-realignment.md)
- [ST-37-04: App presentation decomposition and naming reset](../stories/story-37-04-app-presentation-decomposition-and-naming-reset.md)

## Risks

- If the inventory becomes a mass cancelation pass, valuable script/editor work
  may be lost instead of preserved under the right product framing.
- If UI redesign starts before stale backlog cleanup, the dashboard may inherit
  old "generic tool catalog" or "generic conversion hub" assumptions.
- If Sir Convert-a-Lot remains the default owner for simple app-state edits,
  workflows will keep unnecessary replay, fingerprint, and artifact-overlay
  complexity.
- If generic app presentation is left untouched, teachers will not see the
  product as a set of clear productivity applications.

## Dependencies

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

## Review Gate

`REV-EPIC-37` approved this package on 2026-06-18. `PR-0361` closed the
service-shell UX planning package, and `PR-0362` closed the app-presentation
naming package. The remaining epic work is implementation through `PR-0363`
onward plus the ST-37-04 follow-up slices.

## Implementation Summary

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
  authenticated shell navigation. `ST-37-03` remains open for implementation.
- `PR-0362` is done as of 2026-06-18. It added
  [REF-app-presentation-decomposition-and-naming-plan-v1](../../reference/ref-app-presentation-decomposition-and-naming-plan-v1.md),
  which closes the planning baseline for lane names, descriptions, truthful
  entrypoints, proof gates, and follow-up sequencing for `Klassrumskartan`,
  `Audio Transcription`, `Exam Converter`, and future `Document Converter`.
  `ST-37-04` remains open for implementation through the new follow-up slices
  `PR-0366` through `PR-0369`, while `PR-0363` through `PR-0365` are now
  unblocked by planning and remain gated by their own review docs before code
  implementation begins.
- `PR-0363` is done as of 2026-06-19. It added the authenticated
  `/apps/documents.conversion_hub?mode=exam|transcript` compatibility bridge,
  kept app-id/route/registry/public/backend/Sir Convert/HuleEdu/QTI/DOCX
  surfaces unchanged, retained HuleEdu browser-session proof, and encoded the
  Docker-service breadcrumb for Gateway-backed proof. `ST-37-03` remains open
  for `PR-0364` and `PR-0365`.
- `PR-0364` is ready as of 2026-06-19 and awaits `REV-PR-0364`. It defines
  the authenticated home work-app surface plan: current runnable lanes first,
  no fake Document Converter entry, and script/editor/platform surfaces
  preserved as secondary continuation.
