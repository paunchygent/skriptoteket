---
type: reference
id: REF-app-presentation-decomposition-and-naming-plan-v1
title: "App presentation decomposition and naming plan"
status: active
owners: "agents"
created: 2026-06-18
topic: "app-presentation"
---

# App Presentation Decomposition And Naming Plan

This reference is the durable output of `PR-0362` / `ST-37-04`. It turns the
current product-lane doctrine and service-shell plan into a PR-sized
implementation sequence for app names, descriptions, entrypoints, and future
decomposition work.

This package makes no code, route, registry, backend/API, Sir Convert, HuleEdu,
QTI, DOCX, public-capability, or Document Converter implementation changes.
Those changes remain gated by later reviewed PR slices.

## Governing Inputs

- `EPIC-37` is active and `REV-EPIC-37` is approved.
- `ST-37-04` owns app-presentation decomposition and naming.
- `PR-0360` added
  [REF-current-product-lanes-and-sir-convert-boundary-v1](ref-current-product-lanes-and-sir-convert-boundary-v1.md),
  which remains the authority for native-state versus heavy-conversion
  ownership.
- `PR-0361` added
  [REF-service-shell-ux-realignment-plan-v1](ref-service-shell-ux-realignment-plan-v1.md)
  and created the route-visible shell sequence `PR-0363` through `PR-0365`.

## Current Code Reality

| Surface | Current state | Planning consequence |
|---------|---------------|----------------------|
| `frontend/apps/skriptoteket/src/views/curatedAppHostRegistry.ts` | `classroom.group-seating-studio` has a bespoke host. `documents.conversion_hub` resolves to the authenticated Exam Converter host and the public Exam Converter host. | Klassrumskartan is already a distinct app lane; Exam Converter and Audio Transcription still share one technical compatibility shell. |
| `frontend/apps/skriptoteket/src/views/apps/ExamConverterAuthenticatedView.vue` | The authenticated host keeps `exam` versus `transcript` mode in local component state. | A truthful Audio Transcription entrypoint needs the `PR-0363` query-mode contract before shell links can target it directly. |
| `frontend/apps/skriptoteket/src/router/routes.ts` | Authenticated app routing still centers `/apps/:appId`, while public Exam Converter keeps `/public/apps/documents.conversion_hub/exam-converter`. | This package must not add route aliases, split app ids, or change public routes. |
| `src/skriptoteket/infrastructure/curated_apps/registry.py` | The registry title/summary for `documents.conversion_hub` still describe generic document conversion. | Registry metadata is not yet truthful for the active Exam Converter plus transcript host and needs a separate follow-up slice. |
| `frontend/apps/skriptoteket/src/views/HomeView.vue` and `frontend/apps/skriptoteket/src/components/layout/AuthSidebar.vue` | The signed-in shell is not yet app-first. | `PR-0364` and `PR-0365` should use the lane decisions below after the query-mode bridge exists. |

`documents.conversion_hub` remains a technical compatibility shell until later
reviewed work changes presentation or routes. Product copy and planning should
not use "Conversion Hub" as the teacher-facing concept unless it explicitly
means this historical compatibility surface.

## Lane Naming And Entrypoint Plan

The table below defines the canonical planning baseline for names,
descriptions, route/entrypoint impact, docs impact, and proof gates. It is a
naming/decomposition plan, not a copy lock. Final Swedish UI strings belong to
the copy-only follow-up slice.

| Lane | Canonical lane name | Description baseline | Truthful current entrypoint/status | Docs impact | Route and entrypoint implication | First proof gate |
|------|---------------------|----------------------|------------------------------------|-------------|----------------------------------|------------------|
| `classroom.group-seating-studio` | `Klassrumskartan` | Plan classrooms, groups, seating, rules, exports, and sharing in a native Skriptoteket workspace. | Authenticated `/apps/classroom.group-seating-studio`; public `/public/apps/classroom.group-seating-studio`. | Preserve the existing name across shell, help, and docs surfaces; no decomposition follow-up is needed beyond shell presentation updates. | Preserve the existing dedicated route family unless later reviewed shell work proves a change is needed. | If touched by shell work, use focused home/navigation tests plus browser proof for the changed Klassrumskartan entry. |
| `documents.conversion_hub` transcript mode | `Audio Transcription` | Convert speech or media to saved transcript state, review speakers, and export transcript formats from Skriptoteket-owned transcript state. | Not directly linkable until `PR-0363` adds `/apps/documents.conversion_hub?mode=transcript`; current transcript fixture routes are dev/test surfaces. | Shell, help, and future docs may use the lane name once the query-mode bridge exists; technical docs should keep `documents.conversion_hub` only as compatibility language. | Use the query-mode bridge before any authenticated shell card claims a direct transcript entrypoint. Dedicated route aliases are later route-visible work only. | `PR-0363` focused mode-query tests, `pdm run fe-type-check`, and authenticated HuleEdu browser-session proof for transcript mode. |
| `documents.conversion_hub` exam mode | `Exam Converter` | Import exams, review or correct answer-key state, export files, and grow toward native Skriptoteket exam editing, sharing, and QTI workflows after heavy import. | Authenticated `/apps/documents.conversion_hub` today, then `/apps/documents.conversion_hub?mode=exam` after `PR-0363`; public `/public/apps/documents.conversion_hub/exam-converter` remains the public exam lane. | Future docs and copy must describe post-import correction, editing, sharing, and QTI growth as Skriptoteket-owned exam state rather than producer replay state. | Later route alias or app-id decomposition is optional and must preserve current public Exam Converter truth unless a reviewed follow-up explicitly changes it. | `PR-0363` focused mode-query tests, existing Exam Converter route tests where relevant, `pdm run fe-type-check`, and authenticated HuleEdu browser-session proof for exam mode. |
| document lane | `Document Converter` | Convert and prepare PDF, DOCX, HTML/CSS, Markdown, and template-shaped presentation or document outputs. | Approved as a visible shell/app-shelf lane by the C2 mockup, but no truthful current route or runnable host has been proven yet. | Docs may describe this as an approved product lane, but runtime docs and links must not point to the current compatibility host unless a reviewed route-visible slice makes it truthful. | Do not route teachers to Exam Converter or Audio Transcription under a Document Converter label. A future route or app id needs its own reviewed route-visible slice and proof plan. | Browser proof is valid only after a truthful route target exists. If `PR-0364` reaches implementation without one, it must stop and attach/create the route-visible slice. |

## Change-Family Classification

| Change family | Included work | Explicit exclusions | PR-sized follow-up |
|---------------|---------------|---------------------|--------------------|
| Copy-only | Teacher-facing names, descriptions, headings, tabs, helper copy, and help text that can change without altering routes, app ids, registry records, or backend contracts. | No route alias, no registry metadata change, no backend/API contract change, and no Document Converter host. | `PR-0366` |
| Registry-only | `src/skriptoteket/infrastructure/curated_apps/registry.py` title/summary alignment and any bootstrap/fallback consumers that become truthful once shell copy is aligned. | No app-id split, no route change, no Sir Convert/HuleEdu/QTI/DOCX contract change, and no fake Document Converter implementation. | `PR-0367` |
| Route-visible | Query-mode entrypoints, authenticated home cards, authenticated navigation, and later dedicated teacher-facing route aliases or app-host headings if reviewed as necessary. | No backend/API decomposition unless the route-visible slice proves a concrete incompatibility. | `PR-0363`, `PR-0364`, `PR-0365`, `PR-0368` |
| Backend/API-visible | New bootstrap semantics, public-capability changes, app-detail contract changes, generated types, or app-id decomposition only if route-visible work proves they are necessary. | No Sir Convert producer/Gateway boundary change, no HuleEdu contract change, no QTI/DOCX implementation, and no fake Document Converter implementation. | `PR-0369` |

## Follow-Up PR Sequence

### Existing route-visible foundation

- [PR-0363](../backlog/prs/pr-0363-st-37-03-conversion-lane-mode-deep-link-contract.md):
  add the authenticated query-mode bridge for Exam Converter and Audio
  Transcription on the current compatibility route.
- [PR-0364](../backlog/prs/pr-0364-st-37-03-authenticated-home-work-apps-surface.md):
  make the authenticated home app-first using the approved C2 app shelf. Do not
  fake the Document Converter target; stop or attach the required route-visible
  slice if no truthful route exists.
- [PR-0365](../backlog/prs/pr-0365-st-37-03-authenticated-shell-navigation-realignment.md):
  bring persistent authenticated navigation into the same lane hierarchy.

### ST-37-04 implementation follow-ups

- [PR-0366](../backlog/prs/pr-0366-st-37-04-copy-only-app-lane-naming-and-description-alignment.md):
  align teacher-facing copy across home, navigation, tabs, headings, and help
  without changing routes or registry metadata.
- [PR-0367](../backlog/prs/pr-0367-st-37-04-curated-app-registry-presentation-alignment.md):
  align curated-app registry titles and summaries after route-visible shell
  surfaces are truthful.
- [PR-0368](../backlog/prs/pr-0368-st-37-04-route-visible-app-entrypoint-and-presentation-alignment.md):
  decide whether dedicated teacher-facing route aliases or host-surface route
  presentation are still needed after the compatibility deep-link and shell
  passes ship.
- [PR-0369](../backlog/prs/pr-0369-st-37-04-backend-and-api-app-presentation-contract-alignment.md):
  proceed only if a reviewed route-visible slice proves that route or host
  decomposition cannot stay truthful without bootstrap or API-surface changes.

## Sequencing Rules

1. `PR-0363` must land before any authenticated shell surface claims a direct
   Audio Transcription entrypoint.
2. `PR-0364` and `PR-0365` may present `Klassrumskartan`, `Audio
   Transcription`, `Exam Converter`, `Document Converter`, and
   `Kodredigerare` in the approved app hierarchy. Exam and transcript require
   the query deep-link contract.
3. Document Converter may be visually present as the approved product lane, but
   runtime links must stop unless a reviewed truthful route target exists.
4. Copy-only name/description alignment should happen before registry metadata
   changes so route-visible shell surfaces establish the language first.
5. Registry metadata alignment should happen before any dedicated route alias or
   app-id decomposition, so bootstrap/catalog metadata does not keep advertising
   stale generic document-conversion copy.
6. Backend/API-visible changes are not authorized merely because the current
   technical app id is broad.

## Stop Conditions

- Stop if a proposed runtime change would label the current compatibility host,
  Exam Converter, Audio Transcription, catalog, or any generic fallback as
  Document Converter before a real document route exists.
- Stop if route-visible work tries to split app ids, public routes, registry
  semantics, or backend contracts without going through the later reviewed
  follow-up slices.
- Stop if an Exam Converter follow-up routes native exam state back into Sir
  Convert replay, hash, fingerprint, or artifact-overlay terminology after
  heavy import has completed.
- Stop if any implementation slice needs Sir Convert, HuleEdu, QTI, DOCX, or
  backend/API contract changes not named in its reviewed scope.

## Validation And Proof Expectations

- Copy-only frontend slices: focused Vitest for changed copy surfaces,
  `pdm run fe-type-check`, `pdm run docs-validate`, `git diff --check`, and
  browser proof when visible protected route surfaces change.
- Registry-only slices: focused backend/frontend tests proving exposed
  titles/summaries changed truthfully, `pdm run lint`, `pdm run typecheck` when
  backend code changes, `pdm run docs-validate`, and `git diff --check`.
- Route-visible slices: focused Vitest for route and component behavior,
  `pdm run fe-type-check`, `pdm run docs-validate`, `pdm run handoff-validate`
  when handoff changes, `git diff --check`, and live browser proof through the
  HuleEdu browser-session ceremony for every changed protected route surface.
- Backend/API-visible slices: targeted backend tests, generated-type refresh
  when schemas change, both typecheck lanes, route-visible browser proof if a UI
  consumer changes, `pdm run docs-validate`, and `git diff --check`.
