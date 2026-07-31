---
type: reference
id: REF-SKRIPT-RESEARCH-pr-0358-active-backlog-inventory-and-classification-matrix-PART-01
title: PR-0358 active backlog inventory and classification matrix — part 01
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
root: REF-SKRIPT-RESEARCH-pr-0358-active-backlog-inventory-and-classification-matrix
part: 1
---

## Research Purpose And Boundary
### Summary
| Measure | Count |
|---------|-------|
| Open backlog rows inventoried | 196 |
| Epics | 22 |
| Stories | 68 |
| PR tasks | 106 |
### Deep Audit Revision
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
### Revised PR-0359 Queue
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

## Evidence And Sources
### Source record
This reference is the retained output for `PR-0358`. It inventories every
backlog epic, story, and PR task whose frontmatter status was open at the start
of the slice:

- epics: `proposed`, `active`
- stories: `ready`, `in_progress`, `blocked`
- PR tasks: `ready`, `in_progress`, `blocked`

The snapshot includes `PR-0358` itself while it was still `ready`; the PR task
is closed after this artifact is attached.
### Evidence Keys
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
### First-Pass Inventory Matrix
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
