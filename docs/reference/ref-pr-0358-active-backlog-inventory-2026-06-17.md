---
type: reference
id: REF-pr-0358-active-backlog-inventory-2026-06-17
title: "PR-0358 active backlog inventory and classification matrix"
status: active
owners: "agents"
created: 2026-06-17
topic: "backlog-inventory"
---

# PR-0358 Active Backlog Inventory And Classification Matrix

This reference is the retained output for `PR-0358`. It inventories every
backlog epic, story, and PR task whose frontmatter status was open at the start
of the slice:

- epics: `proposed`, `active`
- stories: `ready`, `in_progress`, `blocked`
- PR tasks: `ready`, `in_progress`, `blocked`

The snapshot includes `PR-0358` itself while it was still `ready`; the PR task
is closed after this artifact is attached.

## Summary

| Measure | Count |
|---------|-------|
| Open backlog rows inventoried | 196 |
| Epics | 22 |
| Stories | 68 |
| PR tasks | 106 |

## First-Pass Classification Counts

These counts are the raw census/classification pass from the initial inventory.
They are retained for traceability, but the deep audit revision below is the
operative recommendation for `PR-0359` and later cleanup. Where the deep audit
conflicts with the first-pass matrix, the deep audit wins.

| Classification | Count | Meaning |
|----------------|-------|---------|
| `keep-active` | 130 | Aligned enough to preserve for now. |
| `needs-decision` | 48 | Requires product/code verification before cleanup. |
| `done-state-repair` | 7 | Existing docs already say implementation shipped; status repair is likely. |
| `split-or-rehome` | 6 | Still valuable, but the current item is too broad or belongs under a newer lane. |
| `superseded-cancel` | 4 | Later architecture/product direction likely replaces this path. |
| `drop-epic` | 1 | Proposed epic appears outside current product direction unless explicitly retained. |

## Deep Audit Revision

This revision responds to review feedback that the first pass was too coarse.
It vets each major domain set against the current codebase and newer done-state
backlog evidence. The goal is to avoid preserving stale open work just because
it is historically valuable, while also avoiding destructive cleanup where code
still depends on the capability.

### Product Lane And Service Shell

**Current code evidence**

- `src/skriptoteket/infrastructure/curated_apps/registry.py` still registers
  `documents.conversion_hub` as "Konvertera dokument", but the active frontend
  host currently routes that app to the Exam Converter bespoke views.
- `frontend/apps/skriptoteket/src/views/HomeView.vue` still presents the signed-in
  dashboard as favorite/recent/tool cards and admin/editor cards. That confirms
  the user-facing shell has not yet caught up with the current app-lane product
  direction.
- The actual app-lane direction is already visible in code: Klassrumskartan,
  Exam Converter, Transcript, Reagent Prep Chef, and Flunk-Out Frenzy are bespoke
  curated-app implementations, not generic script cards.

**Recommendation**

- Keep `EPIC-37` and its PR slices as the governing cleanup/redirection stack.
- Treat `EPIC-16`, `ST-16-08`, and `PR-0057` as split/rehome work. Their old
  browse/catalog framing should not drive the next dashboard; useful density and
  navigation fixes belong under `ST-37-03`/`ST-37-04`.
- Treat `EPIC-08` help rows as rehome candidates rather than automatically
  active. Help for old catalog/results/contributor/admin pages should be recast
  around the current app lanes and editor/runner preservation boundary.

### Conversion, Exam, Transcript, And Document Lanes

**Current code evidence**

- `frontend/apps/skriptoteket/src/views/apps/exam-converter-authenticated/`
  contains the durable authenticated Exam Converter workspace, question review,
  correction-session replay, target artifact, and answer-key UI.
- `frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/` and
  `src/skriptoteket/web/api/v1/apps_conversion_hub_transcript_saves.py` contain
  the saved transcript, speaker-overlay, formatter-export, download, and
  save-to-vault workflow.
- `docs/backlog/epics/epic-21-curated-app-conversion-hub.md` records `PR-0342`,
  `PR-0343`, and the later `ST-21-08`/`ST-21-09` transcript work as done.
- `src/skriptoteket/web/api/v1/public_apps_exam_converter.py` and
  `frontend/apps/skriptoteket/src/views/apps/exam-converter-public/` still
  accept `graded_result_pdf` and `targets_json`. That is stale implementation
  surface: `PR-0357` must move the code with the UI so public intake becomes
  source-only across form state, API parsing, request contracts, and tests.

**Recommendation**

- Split `EPIC-21` into explicit product lanes: Exam Converter, Audio
  Transcription, and Document Converter. The old "Conversion Hub" label is now
  too broad and actively misleading.
- Mark `ST-21-05` and `ST-21-06` as done-state repairs; newer transcript code
  and epic summaries supersede their `ready` status.
- Mark `PR-0325` as done-state repair and cancel `PR-0324`; the blocked
  authenticated E2E proof was overtaken by the runtime remediation and later
  source-only direction.
- Keep `ST-21-10` and `PR-0357` active specifically as a removal/alignment task.
  Public Exam Converter needs the same source-only UI and code contract cleanup
  that authenticated intake already received.
- Split/rehome `ST-21-03` and `PR-0065`: artifact-lane and generic conversion
  assumptions should move into the current Exam Converter and Document Converter
  lanes with the Sir Convert boundary made explicit.

### Klassrumskartan

**Current code evidence**

- `src/skriptoteket/application/curated_apps/classroom_planner/` and
  `frontend/apps/skriptoteket/src/views/apps/classroomPlanner*.ts` show a large,
  active bespoke planner, not a generic script-rendered seating surface.
- Share, public helper, import, smart grouping/seating, fixed-seat, export, and
  guest-upgrade surfaces exist under the classroom planner API/view modules.
- `docs/backlog/epics/epic-29-klassrumskartan-desktop-first-workspace-overhaul.md`
  records several later done slices that absorbed older dense-control work.

**Recommendation**

- Preserve `EPIC-26`, `EPIC-27`, `EPIC-29`, and proposed `EPIC-36`, but keep
  `EPIC-36` behind review approval.
- Mark `PR-0277` as done-state repair only for the implemented thumbnail slice;
  keep `ST-26-07` active because retained review/proof and `PR-0353` remain.
- Cancel or close as absorbed `PR-0195`, `PR-0196`, and `PR-0197` under
  `ST-29-11`. Later done ST-29-11 slices and current shared primitives already
  cover their generic dense-control work.
- Keep later narrow planner follow-ups such as `PR-0225`, `PR-0229`, `ST-29-12`,
  and `PR-0294` only when their specific proof or symbol-rollout scope is still
  current. They should not be treated as evidence that the older ST-29-11 PRs
  are still pending.

### Script, Editor, Runner, File Refs, And Vault

**Current code evidence**

- Runner contract v3, request factory, result parsing, and contract selection
  are implemented under `src/skriptoteket/infrastructure/runner/`.
- First-class file refs and vault are implemented across
  `src/skriptoteket/web/api/v1/tools.py`,
  `src/skriptoteket/web/api/v1/editor/sandbox.py`,
  `src/skriptoteket/web/api/v1/vault.py`,
  `frontend/apps/skriptoteket/src/components/tool-run/ToolFileFieldPicker.vue`,
  `frontend/apps/skriptoteket/src/components/ui-actions/UiActionFieldFileRef.vue`,
  and `frontend/apps/skriptoteket/src/components/vault/`.
- `/editor` MRU/search/tool-menu behavior exists in
  `frontend/apps/skriptoteket/src/views/editor/EditorHubView.vue` and
  `frontend/apps/skriptoteket/src/components/editor/EditorToolMenu.vue`.
- Shared UI primitives from old editor/tool-run cohesion tasks exist:
  `UiSegmentedToggle`, `UiCollapse`, and shared file-picker usage.
- No live `layout_editor_v1` implementation exists in code; Klassrumskartan is
  the bespoke app that now owns classroom layout/seating value.
- `vega_lite` exists in the contract but is deliberately blocked by UI policy
  until restrictions are implemented.

**Recommendation**

- Preserve script/editor/runner as a platform capability, but stop letting old
  generic script concepts own current teacher-facing app lanes.
- Mark `ST-14-24`, `ST-14-36`, `ST-14-38`, `PR-0053`, `PR-0054`, `PR-0055`,
  `PR-0056`, and `PR-0058` as done-state repair candidates.
- Split `EPIC-19`: the runner/file-ref foundation is implemented; `ST-19-07` /
  `PR-0061` is a separate scientific-PDF validation decision, not proof that
  the foundation remains open.
- Cancel/rehome `ST-14-25` through `ST-14-28`. The generic `layout_editor_v1`
  lane is superseded by the bespoke Klassrumskartan architecture.
- Split/rehome `ST-14-33`: script-bank curation can remain, but group-generator
  product value should no longer compete with Klassrumskartan.
- Park `ST-14-35` unless a current platform decision says generic tool datasets
  are still needed. App-native state now owns the main data workflows.
- Keep `ST-14-37` as a policy/implementation decision, not as generic active
  work; the current code intentionally blocks `vega_lite`.
- Audit `PR-0004`, `PR-0005`, `PR-0010`, `PR-0012`, `PR-0024`, and `PR-0026`
  row-by-row before status changes. They are old but touch editor/run contracts
  where partial code may still matter.

### Identity And Auth

**Current code evidence**

- `frontend/apps/skriptoteket/src/router/routes.ts` maps `/register`,
  `/forgot-password`, `/reset-password`, and `/verify-email` to
  `AuthLifecycleHandoffView.vue`.
- `docs/backlog/stories/story-28-08-skriptoteket-standalone-registration-and-password-lifecycle.md`
  records the HuleEdu Gateway lifecycle handoff as done.
- The generated frontend OpenAPI surface no longer exposes local browser
  register/reset/verify endpoints.
- Backend identity token repositories and handlers still exist. They should not
  be deleted during this backlog cleanup without a separate backend/ops
  ownership decision.

**Recommendation**

- Cancel `ST-02-07`, `ST-02-09`, and `PR-0172` as browser-auth superseded by
  the HuleEdu lifecycle ceremony.
- Reclassify `ST-02-06` and `PR-0168` from keep-active to needs-decision/rehome:
  school-domain policy may still matter, but it belongs at the identity provider
  or provisioning boundary, not local Skriptoteket browser registration.
- Recheck `PR-0272` and `PR-0283` under `ST-28-04` for done-state repair against
  the HuleEdu cutover proof before keeping them open.

### SPA And Frontend Platform

**Current code evidence**

- `docs/backlog/epics/epic-30-frontend-transition-continuity-for-same-shell-selectors.md`
  says `ST-30-01` and `ST-30-02` completed through `PR-0165`/`PR-0166`.
- A source scan shows no live `out-in` transition mode usage in the SPA source.
- `frontend/apps/skriptoteket/src/styles/tailwind-theme.css` contains the
  HuleEdu palette/token refresh surface for `ST-11-26`.

**Recommendation**

- Mark `EPIC-30` done-state repair.
- Keep `ST-11-25` active as a platform performance audit.
- Mark `ST-11-26` and `PR-0295` done-state repair.

### Science, Reagent Prep, And Textbook/RAG

**Current code evidence**

- Reagent Prep Chef is not merely a proposal: bespoke frontend, backend API,
  domain, risk, defaults, SDS modal, and export handlers exist.
- Reagent Prep is outside the current top product-lane focus but is an
  implemented curated app and should not be dropped as absent.
- Textbook/RAG remains a proposed research/content lane without clear current
  app-shell priority.

**Recommendation**

- Park or rehome `EPIC-20` as a retained curated app, then audit `ST-20-01` to
  `ST-20-03` and `PR-0059`/`PR-0060`/`PR-0068`/`PR-0072` for done-state repair
  versus remaining SDS/risk gaps.
- Park `EPIC-22`, `ST-22-01`, and `PR-0077` unless the product direction
  explicitly revives textbook/RAG work.

### Games

**Current code evidence**

- Flunk-Out Frenzy exists as a bespoke app with substantial runtime code and
  backend bootstrap seams. It is not dead code.
- Games are not in the current four app-family priorities for the next UI and
  presentation reset.
- `EPIC-31` is a proposed second game and requires review before any
  implementation.

**Recommendation**

- Park `EPIC-25` and `EPIC-33` rather than delete them. They should not consume
  the next product-shell/app-lane tranche unless explicitly revived.
- Drop/cancel `EPIC-31` unless there is a fresh product decision to ship a
  second game.

### Quality, Ops, Security, SEO, Profile

**Recommendation**

- Keep quality, security, observability, and SEO rows active unless they are
  proven stale by code. They are cross-cutting obligations, not product-lane
  vanity.
- Triage `PR-0006` separately because incident-log follow-ups need human
  decision/evidence rather than product-direction inference.
- Park `EPIC-15` / `ST-15-02` until the service-shell and app-lane reset decide
  whether avatar/profile polish matters.

## Evidence Keys

| Key | Evidence or rationale |
|-----|-----------------------|
| K1 | Aligned with current architecture, launch, ops, quality, or security foundation. |
| K2 | Preserved platform capability under the current product-direction reference: script/editor/runner remains valuable when aligned. |
| K3 | Current app-family priority: Klassrumskartan. |
| K4 | Current app-family priority: conversion, exam, transcript, or document lane; verify Sir Convert/native ownership as work proceeds. |
| K5 | Part of `EPIC-37` sequence approved by the user for this inventory tranche. |
| K6 | Help/catalog work is retained for now but should be rechecked during service-shell/app-lane planning. |
| D1 | `EPIC-30` summary says `ST-30-01` and `ST-30-02` completed through `PR-0165`/`PR-0166`. |
| D2 | Development changelog records the palette/token changes and green build/docs checks for `ST-11-26` / `PR-0295`. |
| D3 | `EPIC-21` summary says `PR-0342` proved transcript intake/lifecycle through HuleEdu Gateway. |
| D4 | `EPIC-21` summary says authenticated Exam Converter runtime UI/save remediation was implemented through `PR-0325`. |
| D5 | `EPIC-26` summary says `PR-0277` implemented and deployed preview thumbnails; the story still needs retained review/proof closeout. |
| R1 | Current direction splits generic Conversion Hub into Exam Converter, Audio Transcription, and Document Converter lanes. |
| R2 | `ST-21-10` supersedes optional graded-result upload and early target-selection assumptions. |
| R3 | Catalog/home cleanup should be re-evaluated under service-shell/app-lane presentation work. |
| S1 | `AGENTS.md` and `EPIC-28` put browser auth and password lifecycle under the HuleEdu ceremony. |
| S2 | Blocked authenticated Exam Converter proof was overtaken by `PR-0325` remediation and `ST-21-10` source-only direction. |
| X1 | Proposed side-game epic is outside current four app-family priorities; retain only by explicit decision. |
| N1 | Games are outside the current product-center list; decide retain, pause, or drop before more work. |
| N2 | Science/textbook lanes are outside the four current app-family priorities; decide retain, pause, or drop. |
| N3 | Profile/settings work is not central to the current product reset; decide after shell/app lane priorities. |
| N4 | Parent auth cutover is done; inspect whether the follow-up remains current or stale. |
| N5 | Needs code/docs verification or a product decision before cleanup. |

## First-Pass Inventory Matrix

### Backlog/Product Direction

| Item | Status | Parent | Classification | Evidence |
|------|--------|--------|----------------|----------|
| [EPIC-37](../backlog/epics/epic-37-backlog-product-direction-inventory-and-app-surface-realignment.md) | `proposed` | - | `keep-active` | K5 |
| [PR-0358](../backlog/prs/pr-0358-st-37-01-active-backlog-inventory-and-classification-matrix.md) | `ready` | `ST-37-01` | `keep-active` | K5 |
| [PR-0359](../backlog/prs/pr-0359-st-37-01-stale-state-repair-and-supersession-cleanup-batch.md) | `ready` | `ST-37-01` | `keep-active` | K5 |
| [PR-0360](../backlog/prs/pr-0360-st-37-02-current-product-lane-and-sir-convert-boundary-reference.md) | `ready` | `ST-37-02` | `keep-active` | K5 |
| [PR-0361](../backlog/prs/pr-0361-st-37-03-service-shell-ux-realignment-planning-package.md) | `blocked` | `ST-37-03` | `keep-active` | K5 |
| [PR-0362](../backlog/prs/pr-0362-st-37-04-app-presentation-decomposition-and-naming-package.md) | `blocked` | `ST-37-04` | `keep-active` | K5 |
| [ST-37-01](../backlog/stories/story-37-01-backlog-inventory-and-stale-state-repair.md) | `ready` | `EPIC-37` | `keep-active` | K5 |
| [ST-37-02](../backlog/stories/story-37-02-current-product-lane-and-sir-convert-boundary-reset.md) | `ready` | `EPIC-37` | `keep-active` | K5 |
| [ST-37-03](../backlog/stories/story-37-03-service-shell-and-dashboard-ux-realignment.md) | `blocked` | `EPIC-37` | `keep-active` | K5 |
| [ST-37-04](../backlog/stories/story-37-04-app-presentation-decomposition-and-naming-reset.md) | `blocked` | `EPIC-37` | `keep-active` | K5 |

### Conversion/Exam/Transcript/Document

| Item | Status | Parent | Classification | Evidence |
|------|--------|--------|----------------|----------|
| [EPIC-21](../backlog/epics/epic-21-curated-app-conversion-hub.md) | `active` | - | `split-or-rehome` | R1 |
| [PR-0065](../backlog/prs/pr-0065-conversion-hub-spa-ui-batch-and-preview.md) | `ready` | `ST-21-01` | `split-or-rehome` | R1 |
| [PR-0066](../backlog/prs/pr-0066-migrate-e2e-tests-disable-html-to-pdf-preview-seeding.md) | `ready` | `ST-21-02` | `keep-active` | K4 |
| [PR-0324](../backlog/prs/pr-0324-st-21-03-exam-converter-authenticated-end-to-end-proof.md) | `blocked` | `ST-21-03` | `superseded-cancel` | S2 |
| [PR-0325](../backlog/prs/pr-0325-st-21-03-exam-converter-authenticated-runtime-ui-and-save-remediation.md) | `ready` | `ST-21-03` | `done-state-repair` | D4 |
| [PR-0331](../backlog/prs/pr-0331-st-21-03-exam-converter-reviewed-ai-facit-contract-affordance-reconciliation.md) | `ready` | `ST-21-03` | `keep-active` | K4 |
| [PR-0357](../backlog/prs/pr-0357-st-21-10-public-exam-converter-source-only-alignment.md) | `ready` | `ST-21-10` | `keep-active` | K4 |
| [ST-21-01](../backlog/stories/story-21-01-curated-app-conversion-hub-v1.md) | `in_progress` | `EPIC-21` | `split-or-rehome` | R1 |
| [ST-21-02](../backlog/stories/story-21-02-migrate-off-html-to-pdf-preview-and-retire-tool.md) | `ready` | `EPIC-21` | `keep-active` | K4 |
| [ST-21-03](../backlog/stories/story-21-03-exam-converter-public-and-authenticated-artifact-lanes.md) | `in_progress` | `EPIC-21` | `split-or-rehome` | R2 |
| [ST-21-04](../backlog/stories/story-21-04-exam-converter-durable-teacher-correction-sessions.md) | `ready` | `EPIC-21` | `keep-active` | K4 |
| [ST-21-05](../backlog/stories/story-21-05-conversion-hub-transcript-intake-and-diarization-controls.md) | `ready` | `EPIC-21` | `done-state-repair` | D3 |
| [ST-21-06](../backlog/stories/story-21-06-transcript-job-lifecycle-through-huleedu-gateway.md) | `ready` | `EPIC-21` | `done-state-repair` | D3 |
| [ST-21-10](../backlog/stories/story-21-10-exam-converter-source-only-intake-and-export-owned-formats.md) | `ready` | `EPIC-21` | `keep-active` | K4 |

### Klassrumskartan

| Item | Status | Parent | Classification | Evidence |
|------|--------|--------|----------------|----------|
| [EPIC-26](../backlog/epics/epic-26-klassrumskartan-explicit-exports-and-class-list-import.md) | `active` | - | `keep-active` | K3 |
| [EPIC-27](../backlog/epics/epic-27-klassrumskartan-smart-assignment-v1.md) | `active` | - | `keep-active` | K3 |
| [EPIC-29](../backlog/epics/epic-29-klassrumskartan-desktop-first-workspace-overhaul.md) | `active` | - | `keep-active` | K3 |
| [EPIC-36](../backlog/epics/epic-36-klassrumskartan-scoped-sharing-and-authenticated-import.md) | `proposed` | - | `keep-active` | K3 |
| [PR-0078](../backlog/prs/pr-0078-klassrumskartan-fundamentals-contract-split-and-draft-lifecycle.md) | `ready` | `ST-24-01`, `ST-24-02`, `ST-24-03`, `ST-24-04` | `keep-active` | K3 |
| [PR-0133](../backlog/prs/pr-0133-klassrumskartan-class-list-import-contract-and-service-wiring.md) | `ready` | `ST-26-02` | `keep-active` | K3 |
| [PR-0134](../backlog/prs/pr-0134-klassrumskartan-class-list-import-parsing-heuristics-and-preview-model.md) | `ready` | `ST-26-02` | `keep-active` | K3 |
| [PR-0135](../backlog/prs/pr-0135-klassrumskartan-class-list-import-teacher-preview-ui-and-confirmation-flow.md) | `ready` | `ST-26-02` | `keep-active` | K3 |
| [PR-0136](../backlog/prs/pr-0136-klassrumskartan-seat-drag-preview-and-room-editor-same-tool-toggle-removal.md) | `ready` | `ST-24-04` | `keep-active` | K3 |
| [PR-0138](../backlog/prs/pr-0138-seating-export-single-canonical-sir-convert-v2-key-and-runtime-wiring.md) | `ready` | `ST-26-05` | `keep-active` | K3 |
| [PR-0141](../backlog/prs/pr-0141-klassrumskartan-grouping-pdf-a4-portrait-presentation-renderer-and-delivery.md) | `in_progress` | `ST-26-04` | `keep-active` | K3 |
| [PR-0144](../backlog/prs/pr-0144-klassrumskartan-local-dev-export-runtime-parity-and-schema-remediation.md) | `ready` | `ST-26-03`, `ST-26-04`, `ST-26-05` | `keep-active` | K3 |
| [PR-0160](../backlog/prs/pr-0160-st-29-08-shared-custom-tooltip-primitive-and-dense-tool-adoption.md) | `ready` | `ST-29-08` | `keep-active` | K3 |
| [PR-0167](../backlog/prs/pr-0167-st-27-04-smart-grouping-v1-grouping-history-and-live-seating-influence.md) | `ready` | `ST-27-04` | `keep-active` | K3 |
| [PR-0175](../backlog/prs/pr-0175-klassrumskartan-class-list-import-dropzone-in-create-edit-modal.md) | `in_progress` | `ST-26-02` | `keep-active` | K3 |
| [PR-0178](../backlog/prs/pr-0178-st-27-04-smart-grouping-compactness-simulation-and-overlay-tuning.md) | `in_progress` | `ST-27-04` | `keep-active` | K3 |
| [PR-0187](../backlog/prs/pr-0187-st-29-06-planner-no-classroom-root-cause-hardening-and-error-boundary-remediation.md) | `ready` | `ST-29-06` | `keep-active` | K3 |
| [PR-0195](../backlog/prs/pr-0195-st-29-11-dense-control-primitive-contract-normalization-and-generic-menu-split-behavior.md) | `ready` | `ST-29-11` | `keep-active` | K3 |
| [PR-0196](../backlog/prs/pr-0196-st-29-11-planner-wrapper-thinning-and-action-surface-adapter-cleanup.md) | `ready` | `ST-29-11` | `keep-active` | K3 |
| [PR-0197](../backlog/prs/pr-0197-st-29-11-editor-site-adoption-proof-and-segmented-toggle-contract-completion.md) | `ready` | `ST-29-11` | `keep-active` | K3 |
| [PR-0225](../backlog/prs/pr-0225-st-29-11-desktop-first-planner-toolbar-priority-and-overflow-hardening.md) | `ready` | `ST-29-11` | `keep-active` | K3 |
| [PR-0229](../backlog/prs/pr-0229-st-29-11-desktop-first-planner-toolbar-breakpoint-overflow-escalation-and-undo-redo-shortcut-parity.md) | `ready` | `ST-29-11` | `keep-active` | K3 |
| [PR-0274](../backlog/prs/pr-0274-st-26-06-authenticated-klassrumskartan-shareable-html-css-export-links.md) | `ready` | `ST-26-06` | `keep-active` | K3 |
| [PR-0275](../backlog/prs/pr-0275-st-26-06-share-link-popover-and-bottom-sheet-management.md) | `ready` | `ST-26-06` | `keep-active` | K3 |
| [PR-0277](../backlog/prs/pr-0277-st-26-07-share-link-teams-preview-thumbnails.md) | `in_progress` | `ST-26-07` | `done-state-repair` | D5 |
| [PR-0278](../backlog/prs/pr-0278-st-26-08-shared-print-pdf-visual-redesign.md) | `ready` | `ST-26-08` | `keep-active` | K3 |
| [PR-0294](../backlog/prs/pr-0294-st-29-12-shared-site-symbol-rollout-and-guardrails.md) | `ready` | `ST-29-12` | `keep-active` | K3 |
| [PR-0297](../backlog/prs/pr-0297-st-27-09-fixed-seat-rule-persistence-and-solver-seeding.md) | `ready` | `ST-27-09` | `keep-active` | K3 |
| [PR-0298](../backlog/prs/pr-0298-st-27-09-fixed-seat-tool-and-classroom-view-first-rules-ux.md) | `ready` | `ST-27-09` | `keep-active` | K3 |
| [PR-0313](../backlog/prs/pr-0313-shared-phone-classroom-map-real-device-pinch-remediation.md) | `in_progress` | `ST-27-09`, `ST-29-16`, `ST-29-17` | `keep-active` | K3 |
| [PR-0314](../backlog/prs/pr-0314-solver-owned-rule-marker-semantics.md) | `in_progress` | `ST-27-09`, `ST-29-12`, `ST-29-16`, `ST-29-17` | `keep-active` | K3 |
| [PR-0315](../backlog/prs/pr-0315-st-29-17-phone-rules-active-rule-management.md) | `in_progress` | `ST-29-17`, `ST-27-09` | `keep-active` | K3 |
| [PR-0353](../backlog/prs/pr-0353-st-26-07-production-playwright-dep0169-remediation.md) | `ready` | `ST-26-07` | `keep-active` | K3 |
| [ST-26-02](../backlog/stories/story-26-02-klassrumskartan-class-list-import-from-file-with-preview-and-confirmation.md) | `ready` | `EPIC-26` | `keep-active` | K3 |
| [ST-26-04](../backlog/stories/story-26-04-klassrumskartan-grouping-pdf-export.md) | `ready` | `EPIC-26` | `keep-active` | K3 |
| [ST-26-06](../backlog/stories/story-26-06-klassrumskartan-shareable-html-css-export-links.md) | `ready` | `EPIC-26` | `keep-active` | K3 |
| [ST-26-07](../backlog/stories/story-26-07-klassrumskartan-share-link-teams-preview-thumbnails.md) | `in_progress` | `EPIC-26` | `keep-active` | K3 |
| [ST-26-08](../backlog/stories/story-26-08-klassrumskartan-shared-print-pdf-visual-parity.md) | `ready` | `EPIC-26` | `keep-active` | K3 |
| [ST-27-04](../backlog/stories/story-27-04-klassrumskartan-smart-grouping-v1.md) | `in_progress` | `EPIC-27` | `keep-active` | K3 |
| [ST-27-05](../backlog/stories/story-27-05-klassrumskartan-smart-explanations-and-alternate-options.md) | `ready` | `EPIC-27` | `keep-active` | K3 |
| [ST-27-09](../backlog/stories/story-27-09-klassrumskartan-fixed-seat-rules-and-classroom-view-first-authoring.md) | `ready` | `EPIC-27` | `keep-active` | K3 |
| [ST-29-08](../backlog/stories/story-29-08-klassrumskartan-shared-custom-tooltip-system-and-global-hover-contract.md) | `ready` | `EPIC-29` | `keep-active` | K3 |
| [ST-29-11](../backlog/stories/story-29-11-klassrumskartan-shared-site-and-app-dense-control-primitive-tightening.md) | `ready` | `EPIC-29` | `keep-active` | K3 |
| [ST-29-12](../backlog/stories/story-29-12-klassrumskartan-canonical-symbol-language-and-discoverability-contract-completion.md) | `ready` | `EPIC-29` | `keep-active` | K3 |

### Script/Editor/Runner

| Item | Status | Parent | Classification | Evidence |
|------|--------|--------|----------------|----------|
| [EPIC-14](../backlog/epics/epic-14-admin-tool-authoring.md) | `active` | - | `keep-active` | K2 |
| [EPIC-19](../backlog/epics/epic-19-runner-io-and-file-references-foundations.md) | `active` | - | `keep-active` | K2 |
| [PR-0004](../backlog/prs/pr-0004-sandbox-transient-settings-input-multi-enum-clear-settings.md) | `ready` | `ST-14-05`, `ST-14-08`, `ST-12-03`, `ST-12-04` | `keep-active` | K2 |
| [PR-0005](../backlog/prs/pr-0005-contract-v2-help-template-update.md) | `ready` | `ST-14-29`, `ST-14-23`, `ST-14-24`, `ST-14-25` | `keep-active` | K2 |
| [PR-0010](../backlog/prs/pr-0010-editor-save-restore-ux-clarity.md) | `ready` | - | `keep-active` | K2 |
| [PR-0012](../backlog/prs/pr-0012-editor-cohesion-pass-input-selectors.md) | `in_progress` | `ST-14-32` | `keep-active` | K2 |
| [PR-0024](../backlog/prs/pr-0024-action-payload-skriptoteket-action-docs-prompt-alignment.md) | `ready` | `ST-14-19` | `keep-active` | K2 |
| [PR-0025](../backlog/prs/pr-0025-script-bank-curation-and-group-generator.md) | `ready` | `ST-14-33` | `keep-active` | K2 |
| [PR-0026](../backlog/prs/pr-0026-settings-suggestions-from-tool-runs.md) | `ready` | `ST-14-34` | `keep-active` | K2 |
| [PR-0053](../backlog/prs/pr-0053-ui-contract-file-ref-picker-and-defaults.md) | `ready` | `ST-14-24` | `keep-active` | K2 |
| [PR-0054](../backlog/prs/pr-0054-user-file-vault-backend-and-resolver.md) | `ready` | `ST-14-36` | `keep-active` | K2 |
| [PR-0055](../backlog/prs/pr-0055-user-file-vault-ui-picker.md) | `ready` | `ST-14-36` | `keep-active` | K2 |
| [PR-0056](../backlog/prs/pr-0056-shared-segmented-toggle-and-file-picker-row.md) | `in_progress` | `ST-14-22` | `keep-active` | K2 |
| [PR-0058](../backlog/prs/pr-0058-kodredigerare-verktygsval-och-sok.md) | `in_progress` | `ST-14-38` | `keep-active` | K2 |
| [PR-0061](../backlog/prs/pr-0061-story-003c-thin-adapter-parity-and-scientific-pdf-workload-validation.md) | `ready` | `ST-19-07` | `keep-active` | K2 |
| [ST-14-22](../backlog/stories/story-14-22-tool-run-ux-progress-and-file-references.md) | `ready` | `EPIC-14` | `keep-active` | K2 |
| [ST-14-24](../backlog/stories/story-14-24-ui-contract-file-references.md) | `ready` | `EPIC-14` | `keep-active` | K2 |
| [ST-14-25](../backlog/stories/story-14-25-ui-contract-layout-editor-v1-output.md) | `ready` | `EPIC-14` | `keep-active` | K2 |
| [ST-14-26](../backlog/stories/story-14-26-ui-renderer-layout-editor-v1-click-assign.md) | `ready` | `EPIC-14` | `keep-active` | K2 |
| [ST-14-27](../backlog/stories/story-14-27-layout-editor-v1-drag-drop.md) | `ready` | `EPIC-14` | `keep-active` | K2 |
| [ST-14-28](../backlog/stories/story-14-28-layout-editor-v1-ux-polish-and-a11y.md) | `ready` | `EPIC-14` | `keep-active` | K2 |
| [ST-14-29](../backlog/stories/story-14-29-editor-pro-mode-combined-bundle-view.md) | `ready` | `EPIC-14` | `keep-active` | K2 |
| [ST-14-32](../backlog/stories/story-14-32-editor-cohesion-pass-input-selectors.md) | `in_progress` | `EPIC-14` | `keep-active` | K2 |
| [ST-14-33](../backlog/stories/story-14-33-script-bank-curation-and-group-generator.md) | `ready` | `EPIC-14` | `keep-active` | K2 |
| [ST-14-34](../backlog/stories/story-14-34-settings-suggestions-from-tool-runs.md) | `ready` | `EPIC-14` | `keep-active` | K2 |
| [ST-14-35](../backlog/stories/story-14-35-tool-datasets-crud-and-picker.md) | `ready` | `EPIC-14` | `keep-active` | K2 |
| [ST-14-36](../backlog/stories/story-14-36-user-file-vault-and-picker.md) | `ready` | `EPIC-14` | `keep-active` | K2 |
| [ST-14-37](../backlog/stories/story-14-37-ui-output-vega-lite.md) | `ready` | `EPIC-14` | `keep-active` | K2 |
| [ST-14-38](../backlog/stories/story-14-38-kodredigerare-verktygsval-och-sok.md) | `in_progress` | `EPIC-14` | `keep-active` | K2 |
| [ST-19-07](../backlog/stories/story-19-07-story-003c-thin-adapter-consumer-adoption-and-scientific-pdf-workload.md) | `ready` | `EPIC-19` | `keep-active` | K2 |

### Shell/Catalog/Help

| Item | Status | Parent | Classification | Evidence |
|------|--------|--------|----------------|----------|
| [EPIC-08](../backlog/epics/epic-08-contextual-help-and-onboarding.md) | `active` | - | `keep-active` | K6 |
| [EPIC-16](../backlog/epics/epic-16-catalog-discovery-and-personalization.md) | `active` | - | `keep-active` | K6 |
| [PR-0020](../backlog/prs/pr-0020-ai-frontend-srp-refactor-audit-hotspots.md) | `ready` | `ST-08-14`, `ST-08-20`, `ST-08-21`, `ST-08-22`, `ST-08-23`, `ST-08-24`, `ST-08-25`, `ST-08-26`, `ST-08-27` | `keep-active` | K6 |
| [PR-0022](../backlog/prs/pr-0022-editor-chat-virtual-file-context-retention.md) | `ready` | `ST-08-27` | `keep-active` | K6 |
| [PR-0023](../backlog/prs/pr-0023-tokenizer-backed-prompt-budgeting.md) | `ready` | `ST-08-27` | `keep-active` | K6 |
| [PR-0027](../backlog/prs/pr-0027-ai-chat-ops-system-prompt-budget-followups.md) | `ready` | `ST-08-21`, `ST-08-23`, `ST-08-27` | `keep-active` | K6 |
| [PR-0037](../backlog/prs/pr-0037-editor-ai-edit-ops-tolerant-diff-matching.md) | `ready` | `ST-08-24` | `keep-active` | K6 |
| [PR-0271](../backlog/prs/pr-0271-st-08-35-help-completion-route-coverage-and-copy-signoff.md) | `ready` | `ST-08-35` | `keep-active` | K6 |
| [ST-08-04](../backlog/stories/story-08-04-catalog-help.md) | `ready` | `EPIC-08` | `keep-active` | K6 |
| [ST-08-05](../backlog/stories/story-08-05-results-and-downloads-help.md) | `ready` | `EPIC-08` | `keep-active` | K6 |
| [ST-08-06](../backlog/stories/story-08-06-contributor-help.md) | `ready` | `EPIC-08` | `keep-active` | K6 |
| [ST-08-07](../backlog/stories/story-08-07-admin-dashboard-help.md) | `ready` | `EPIC-08` | `keep-active` | K6 |
| [ST-08-08](../backlog/stories/story-08-08-editor-help-overview.md) | `ready` | `EPIC-08` | `keep-active` | K6 |
| [ST-08-09](../backlog/stories/story-08-09-editor-help-test-area.md) | `ready` | `EPIC-08` | `keep-active` | K6 |
| [ST-08-17](../backlog/stories/story-08-17-tabby-edit-suggestions-ab-testing.md) | `ready` | `EPIC-08` | `keep-active` | K6 |
| [ST-08-27](../backlog/stories/story-08-27-editor-chat-virtual-file-context-retention-and-tokenizers.md) | `ready` | `EPIC-08` | `keep-active` | K6 |
| [ST-08-35](../backlog/stories/story-08-35-help-completion-route-coverage-and-copy-signoff.md) | `ready` | `EPIC-08` | `keep-active` | K6 |
| [ST-16-08](../backlog/stories/story-16-08-catalog-cleanup-and-review.md) | `ready` | `EPIC-16` | `split-or-rehome` | R3 |

### SPA/Frontend Platform

| Item | Status | Parent | Classification | Evidence |
|------|--------|--------|----------------|----------|
| [EPIC-11](../backlog/epics/epic-11-full-vue-spa-migration.md) | `active` | - | `keep-active` | K1 |
| [EPIC-30](../backlog/epics/epic-30-frontend-transition-continuity-for-same-shell-selectors.md) | `active` | - | `done-state-repair` | D1 |
| [PR-0057](../backlog/prs/pr-0057-browse-cta-removal-and-toolrunview-density-transition-polish.md) | `in_progress` | `ST-16-05`, `ST-11-07` | `split-or-rehome` | R3 |
| [PR-0241](../backlog/prs/pr-0241-st-11-25-playwright-tree-normalization.md) | `ready` | `ST-11-25` | `keep-active` | K1 |
| [PR-0243](../backlog/prs/pr-0243-st-11-25-lhci-and-bundle-visualizer-toolchain.md) | `ready` | `ST-11-25` | `keep-active` | K1 |
| [PR-0244](../backlog/prs/pr-0244-st-11-25-pilot-route-inventory-and-trace-baselines.md) | `ready` | `ST-11-25` | `keep-active` | K1 |
| [PR-0295](../backlog/prs/pr-0295-st-11-26-huleedu-palette-token-refresh.md) | `in_progress` | `ST-11-26` | `done-state-repair` | D2 |
| [ST-11-25](../backlog/stories/story-11-25-spa-route-load-performance-and-network-isolation-audit.md) | `ready` | `EPIC-11` | `keep-active` | K1 |
| [ST-11-26](../backlog/stories/story-11-26-huleedu-palette-token-refresh.md) | `in_progress` | `EPIC-11` | `done-state-repair` | D2 |

### Identity/Auth

| Item | Status | Parent | Classification | Evidence |
|------|--------|--------|----------------|----------|
| [EPIC-02](../backlog/epics/epic-02-identity-and-access-control.md) | `active` | - | `keep-active` | K1 |
| [PR-0168](../backlog/prs/pr-0168-swedish-school-domain-allowlist.md) | `ready` | `ST-02-06` | `keep-active` | K1 |
| [PR-0172](../backlog/prs/pr-0172-local-password-reset-via-emailed-token.md) | `ready` | `ST-02-07` | `superseded-cancel` | S1 |
| [PR-0272](../backlog/prs/pr-0272-st-28-04-huleedu-internal-identity-header-spelling-remediation.md) | `ready` | `ST-28-04` | `needs-decision` | N4 |
| [PR-0283](../backlog/prs/pr-0283-st-28-04-local-auth-edge-bootstrap-preflight.md) | `ready` | `ST-28-04` | `needs-decision` | N4 |
| [ST-02-02](../backlog/stories/story-02-02-admin-nomination-and-superuser-approval.md) | `ready` | `EPIC-02` | `keep-active` | K1 |
| [ST-02-06](../backlog/stories/story-02-06-swedish-school-domain-allowlist-registration.md) | `ready` | `EPIC-02` | `keep-active` | K1 |
| [ST-02-07](../backlog/stories/story-02-07-local-password-reset-via-emailed-token.md) | `ready` | `EPIC-02` | `superseded-cancel` | S1 |
| [ST-02-09](../backlog/stories/story-02-09-distributed-password-reset-hardening-for-scaled-auth.md) | `ready` | `EPIC-02` | `superseded-cancel` | S1 |

### Quality/Ops/Security/SEO

| Item | Status | Parent | Classification | Evidence |
|------|--------|--------|----------------|----------|
| [EPIC-06](../backlog/epics/epic-06-quality-and-test-coverage.md) | `active` | - | `keep-active` | K1 |
| [EPIC-09](../backlog/epics/epic-09-security-hardening.md) | `active` | - | `keep-active` | K1 |
| [EPIC-35](../backlog/epics/epic-35-launch-seo-and-search-indexing-readiness.md) | `active` | - | `keep-active` | K1 |
| [PR-0006](../backlog/prs/pr-0006-hemma-incident-log-findings-2026-01-06.md) | `ready` | - | `needs-decision` | N5 |
| [PR-0044](../backlog/prs/pr-0044-llm-telemetry-and-stats.md) | `ready` | `ST-08-14`, `ST-07-02` | `keep-active` | K1 |
| [PR-0049](../backlog/prs/pr-0049-backend-srp-refactor-god-modules.md) | `ready` | `ST-06-16` | `keep-active` | K1 |
| [PR-0162](../backlog/prs/pr-0162-st-07-07-public-http-dishka-adapter-and-observability-cutover.md) | `ready` | `ST-07-07` | `keep-active` | K1 |
| [PR-0163](../backlog/prs/pr-0163-st-07-07-http-route-dependency-cutover-off-hybrid-dishka-inject.md) | `ready` | `ST-07-07` | `keep-active` | K1 |
| [PR-0164](../backlog/prs/pr-0164-st-07-07-websocket-cutover-hybrid-compat-retirement-and-production-proof.md) | `ready` | `ST-07-07` | `keep-active` | K1 |
| [PR-0170](../backlog/prs/pr-0170-st-09-07-public-edge-app-runtime-hardening.md) | `in_progress` | `ST-09-07` | `keep-active` | K1 |
| [PR-0171](../backlog/prs/pr-0171-st-09-08-hemma-edge-observability-and-host-lockdown.md) | `ready` | `ST-09-08` | `keep-active` | K1 |
| [ST-06-16](../backlog/stories/story-06-16-backend-srp-refactor-god-modules.md) | `ready` | `EPIC-06` | `keep-active` | K1 |
| [ST-09-05](../backlog/stories/story-09-05-content-security-policy-spa.md) | `ready` | `EPIC-09` | `keep-active` | K1 |
| [ST-09-07](../backlog/stories/story-09-07-public-edge-app-runtime-hardening.md) | `in_progress` | `EPIC-09` | `keep-active` | K1 |
| [ST-09-08](../backlog/stories/story-09-08-hemma-edge-observability-and-host-lockdown.md) | `ready` | `EPIC-09` | `keep-active` | K1 |
| [ST-35-04](../backlog/stories/story-35-04-search-console-bing-and-launch-day-seo-operations.md) | `blocked` | `EPIC-35` | `keep-active` | K1 |

### Science/Textbook Apps

| Item | Status | Parent | Classification | Evidence |
|------|--------|--------|----------------|----------|
| [EPIC-20](../backlog/epics/epic-20-curated-app-reagent-prep-chef.md) | `proposed` | - | `needs-decision` | N2 |
| [EPIC-22](../backlog/epics/epic-22-textbook-corpus-pristine-cleanup-and-rag-readiness.md) | `proposed` | - | `needs-decision` | N2 |
| [PR-0059](../backlog/prs/pr-0059-curated-app-reagent-prep-chef.md) | `ready` | `ST-20-01` | `needs-decision` | N2 |
| [PR-0060](../backlog/prs/pr-0060-curated-app-reagent-prep-chef-risk-assessment.md) | `in_progress` | `ST-20-02` | `needs-decision` | N2 |
| [PR-0068](../backlog/prs/pr-0068-reagent-prep-chef-sds-pdfs-manual-download.md) | `ready` | `ST-20-03` | `needs-decision` | N2 |
| [PR-0072](../backlog/prs/pr-0072-reagent-prep-chef-risk-texts-from-hazards-sds-aligned.md) | `in_progress` | `ST-20-02` | `needs-decision` | N2 |
| [PR-0077](../backlog/prs/pr-0077-textbook-corpus-rag-packaging-and-postgresql-vector-ingest-contract.md) | `ready` | `ST-22-01` | `needs-decision` | N2 |
| [ST-20-01](../backlog/stories/story-20-01-curated-app-reagent-prep-chef.md) | `ready` | `EPIC-20` | `needs-decision` | N2 |
| [ST-20-02](../backlog/stories/story-20-02-curated-app-reagent-prep-chef-risk-assessment.md) | `in_progress` | `EPIC-20` | `needs-decision` | N2 |
| [ST-20-03](../backlog/stories/story-20-03-curated-app-reagent-prep-chef-sds-corpus.md) | `ready` | `EPIC-20` | `needs-decision` | N2 |
| [ST-22-01](../backlog/stories/story-22-01-textbook-corpus-cleanup-pipeline-and-manual-restoration-workflow.md) | `ready` | `EPIC-22` | `needs-decision` | N2 |

### Games

| Item | Status | Parent | Classification | Evidence |
|------|--------|--------|----------------|----------|
| [EPIC-25](../backlog/epics/epic-25-competitive-games-and-flunk-out-frenzy.md) | `active` | - | `needs-decision` | N1 |
| [EPIC-31](../backlog/epics/epic-31-flappy-birds-curated-app.md) | `proposed` | - | `drop-epic` | X1 |
| [EPIC-33](../backlog/epics/epic-33-flunk-out-frenzy-physical-carrier-foundations-and-cutover-governance.md) | `active` | - | `needs-decision` | N1 |
| [PR-0108](../backlog/prs/pr-0108-flunk-out-frenzy-runtime-lazy-load-and-game-bundle-splitting.md) | `ready` | `ST-25-02` | `needs-decision` | N1 |
| [PR-0190](../backlog/prs/pr-0190-flunk-out-frenzy-bonus-jackpot-and-ball-lifecycle-rule-state.md) | `ready` | `ST-25-05` | `needs-decision` | N1 |
| [PR-0192](../backlog/prs/pr-0192-flunk-out-frenzy-flipper-contact-model-and-explicit-launcher-state.md) | `ready` | `ST-25-05` | `needs-decision` | N1 |
| [PR-0193](../backlog/prs/pr-0193-flunk-out-frenzy-capture-eject-and-save-devices.md) | `ready` | `ST-25-05` | `needs-decision` | N1 |
| [PR-0194](../backlog/prs/pr-0194-flunk-out-frenzy-ramps-gates-and-field-zone-semantics.md) | `ready` | `ST-25-05` | `needs-decision` | N1 |
| [PR-0195](../backlog/prs/pr-0195-flunk-out-frenzy-objective-controllers-and-bank-progression.md) | `ready` | `ST-25-05` | `needs-decision` | N1 |
| [PR-0198](../backlog/prs/pr-0198-flunk-out-frenzy-vpw-donor-topology-and-spec-cutover.md) | `in_progress` | `ST-25-06` | `needs-decision` | N1 |
| [PR-0199](../backlog/prs/pr-0199-flunk-out-frenzy-donor-semantic-representation-and-trigger-shape-fidelity.md) | `ready` | `ST-25-06` | `needs-decision` | N1 |
| [PR-0200](../backlog/prs/pr-0200-flunk-out-frenzy-launcher-release-path-and-donor-wall-face-representation.md) | `blocked` | `ST-25-06` | `needs-decision` | N1 |
| [PR-0201](../backlog/prs/pr-0201-flunk-out-frenzy-shooter-corridor-wall263-de-overlap.md) | `in_progress` | `ST-25-06` | `needs-decision` | N1 |
| [PR-0202](../backlog/prs/pr-0202-flunk-out-frenzy-full-board-donor-3d-carrier-mapping-and-elevated-rails.md) | `blocked` | `ST-25-06` | `needs-decision` | N1 |
| [PR-0203](../backlog/prs/pr-0203-flunk-out-frenzy-elevated-rail-travel-and-left-handoff-mechanics.md) | `blocked` | `ST-25-06` | `needs-decision` | N1 |
| [PR-0204](../backlog/prs/pr-0204-flunk-out-frenzy-ruthless-review-gate-for-launcher-input-and-overlay-seam.md) | `ready` | `ST-25-06` | `needs-decision` | N1 |
| [PR-0205](../backlog/prs/pr-0205-flunk-out-frenzy-launcher-root-cause-proof-and-input-lifecycle-fix-plan.md) | `ready` | `ST-25-06` | `needs-decision` | N1 |
| [PR-0206](../backlog/prs/pr-0206-flunk-out-frenzy-plunger-strike-root-cause-proof-and-telemetry-contract.md) | `ready` | `ST-25-06` | `needs-decision` | N1 |
| [PR-0207](../backlog/prs/pr-0207-flunk-out-frenzy-launcher-strike-ready-rest-pose-alignment.md) | `ready` | `ST-25-06` | `needs-decision` | N1 |
| [PR-0208](../backlog/prs/pr-0208-flunk-out-frenzy-strike-ready-rest-pose-and-release-integration-fix.md) | `ready` | `ST-25-06` | `needs-decision` | N1 |
| [PR-0209](../backlog/prs/pr-0209-flunk-out-frenzy-end-to-end-launch-to-drop-telemetry-contract.md) | `ready` | `ST-25-06` | `needs-decision` | N1 |
| [PR-0210](../backlog/prs/pr-0210-flunk-out-frenzy-file-size-compliance-and-frontend-module-decomposition.md) | `ready` | `ST-25-05` | `needs-decision` | N1 |
| [PR-0212](../backlog/prs/pr-0212-flunk-out-frenzy-launcher-shortcut-breach-inventory-and-truth-gate-audit.md) | `ready` | `ST-25-06` | `needs-decision` | N1 |
| [PR-0215](../backlog/prs/pr-0215-flunk-out-frenzy-launcher-runtime-shortcut-remediation-and-physical-truth-alignment.md) | `in_progress` | `ST-25-06` | `needs-decision` | N1 |
| [PR-0216](../backlog/prs/pr-0216-flunk-out-frenzy-physical-rail-carrier-semantics-and-architect-guidance-packet.md) | `ready` | `ST-25-06` | `needs-decision` | N1 |
| [PR-0217](../backlog/prs/pr-0217-flunk-out-frenzy-carrier-role-schema-observation-spine-contract-and-launcher-world-ownership-rules.md) | `ready` | `ST-33-01` | `needs-decision` | N1 |
| [PR-0218](../backlog/prs/pr-0218-flunk-out-frenzy-launcher-world-carrier-compiler-and-donor-overhead-collider-foundation.md) | `ready` | `ST-33-01` | `needs-decision` | N1 |
| [PR-0219](../backlog/prs/pr-0219-flunk-out-frenzy-physical-carrier-observer-shadow-mode-and-cutover-readiness-gate.md) | `ready` | `ST-33-01` | `needs-decision` | N1 |
| [ST-25-03](../backlog/stories/story-25-03-competitive-play-pending-score-submission-and-typed-leaderboards.md) | `ready` | `EPIC-25` | `needs-decision` | N1 |
| [ST-25-04](../backlog/stories/story-25-04-competitive-play-leaderboard-hardening-and-ruleset-scoping.md) | `ready` | `EPIC-25` | `needs-decision` | N1 |
| [ST-25-05](../backlog/stories/story-25-05-flunk-out-frenzy-mechanics-port-foundation.md) | `in_progress` | `EPIC-25` | `needs-decision` | N1 |
| [ST-25-06](../backlog/stories/story-25-06-flunk-out-frenzy-vpw-donor-topology-and-table-spec-rebuild.md) | `in_progress` | `EPIC-25` | `needs-decision` | N1 |
| [ST-33-01](../backlog/stories/story-33-01-flunk-out-frenzy-physical-carrier-foundations-and-cutover-governance.md) | `ready` | `EPIC-33` | `needs-decision` | N1 |

### Profile/Settings

| Item | Status | Parent | Classification | Evidence |
|------|--------|--------|----------------|----------|
| [EPIC-15](../backlog/epics/epic-15-user-profile-and-settings.md) | `active` | - | `needs-decision` | N3 |
| [ST-15-02](../backlog/stories/story-15-02-avatar-upload.md) | `blocked` | `EPIC-15` | `needs-decision` | N3 |

## Revised PR-0359 Queue

`PR-0359` should operate from this revised queue, not from the raw first-pass
counts. Keep the cleanup batch small enough that every status change can cite
code or newer backlog evidence.

### Safe Done-State Repairs

- `EPIC-30`: completed by `PR-0165`/`PR-0166`; source scan shows no live
  `out-in` transition mode.
- `ST-11-26` and `PR-0295`: HuleEdu palette/token refresh exists in the SPA
  theme surface.
- `ST-21-05` and `ST-21-06`: transcript intake/job lifecycle is implemented and
  later EPIC-21 summaries record the Gateway/STT proof.
- `PR-0325`: authenticated Exam Converter runtime UI/save remediation is
  implemented and supersedes the blocked proof-only slice.
- `PR-0277`: share-preview thumbnail implementation is done; do not close
  `ST-26-07` until retained review/proof and `PR-0353` are resolved.
- `ST-14-24`, `ST-14-36`, `ST-14-38`, `PR-0053`, `PR-0054`, `PR-0055`,
  `PR-0056`, and `PR-0058`: file-ref, vault, shared segmented/file-picker UI,
  collapse transition, and editor MRU/search/tool-menu code exist.

### Superseded Or Absorbed Rows

- `ST-02-07`, `ST-02-09`, and `PR-0172`: local browser password lifecycle is
  superseded by the done HuleEdu lifecycle handoff. Preserve backend identity
  artifacts until a separate backend ownership decision exists.
- `PR-0324`: blocked authenticated Exam Converter proof is superseded by
  `PR-0325` plus the later source-only direction.
- `ST-14-25`, `ST-14-26`, `ST-14-27`, and `ST-14-28`: generic
  `layout_editor_v1` work is superseded by the bespoke Klassrumskartan app.
- `PR-0195`, `PR-0196`, and `PR-0197` under `ST-29-11`: absorbed by later
  ST-29-11 done slices and current dense-control primitives.
- `EPIC-31`: drop/cancel candidate unless the product direction explicitly
  revives a second competitive game.

### Split Or Rehome

- `EPIC-21`, `ST-21-01`, `ST-21-03`, and `PR-0065`: split into Exam Converter,
  Audio Transcription, and Document Converter lanes; make Sir Convert ownership
  explicit for heavy conversion and keep native app state inside Skriptoteket.
- `EPIC-14` and `EPIC-19`: preserve editor/runner capability but split old
  platform foundation rows from narrow validation or app-superseded work.
- `ST-14-22`: file-ref work is done through narrower rows; progress UX should
  survive only as a small current tool-run UX task.
- `ST-14-33`: retain script-bank curation if useful, but rehome group-generator
  product value to Klassrumskartan.
- `ST-16-08`, `PR-0057`, and the old shell/catalog/help rows: rehome under the
  service-shell and app-presentation reset instead of preserving old browse-card
  framing.
- `ST-02-06` and `PR-0168`: rehome any Swedish-school-domain policy to the
  HuleEdu identity/provisioning boundary, or park until that owner accepts it.

### Keep Active For Immediate Product Direction

- `ST-21-10` and `PR-0357`: public Exam Converter still has stale optional
  graded-PDF/target-selection fields in UI/API code; the slice must remove the
  code paths together with the UI.
- `ST-37-02`, `ST-37-03`, and `ST-37-04`: current product-lane, service-shell,
  and app-presentation reset.
- Current Klassrumskartan follow-ups that have not been replaced by newer code
  or proof, especially `ST-26-07`/`PR-0353`, `ST-26-08`, `ST-27-04`,
  `ST-27-05`, `ST-27-09`, `ST-29-08`, `ST-29-12`, and proposed `EPIC-36`
  after review approval.
- `ST-11-25` and cross-cutting quality/security/ops/SEO rows unless a
  row-specific code audit proves them stale.

### Park Or Decide Before Status Changes

- `EPIC-20`: implemented Reagent Prep app exists, but it is outside the current
  top-lane focus; audit child rows for done-state repair versus remaining SDS
  and risk gaps.
- `EPIC-22`: park textbook/RAG until revived.
- `EPIC-25` and `EPIC-33`: park games without deleting implemented Flunk-Out
  Frenzy code.
- `EPIC-15` / `ST-15-02`: defer profile/avatar work until the service-shell
  reset sets profile importance.
- `PR-0006`, `PR-0004`, `PR-0005`, `PR-0010`, `PR-0012`, `PR-0024`, and
  `PR-0026`: require row-specific audit because they touch old-but-still-useful
  editor/run/ops contracts.

Rows marked `needs-decision` should not be canceled during `PR-0359` unless a
separate product decision closes the uncertainty first.
