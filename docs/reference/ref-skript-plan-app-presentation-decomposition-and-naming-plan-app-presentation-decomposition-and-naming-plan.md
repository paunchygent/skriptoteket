---
type: reference
id: REF-SKRIPT-PLAN-app-presentation-decomposition-and-naming-plan
title: App presentation decomposition and naming plan
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: active
reference_kind: plan
retired_ids:
- REF-app-presentation-decomposition-and-naming-plan-v1
summary: App presentation decomposition and naming plan
---

## Outcome And Purpose

Source: `docs/reference/ref-app-presentation-decomposition-and-naming-plan-v1.md`. App presentation decomposition and naming plan.

This reference is the durable output of `PR-0362` / `ST-37-04`. It turns the current product-lane doctrine and service-shell plan into a PR-sized implementation sequence for app names, descriptions, entrypoints, and future decomposition work. This package makes no code, route, registry, backend/API, Sir Convert, HuleEdu, QTI, DOCX, public-capability, or Document Converter implementation changes. Those changes remain gated by later reviewed PR slices. - `EPIC-37` is active and `REV-EPIC-37` is approved. - `ST-37-04` owns app-presentation decomposition and naming. - `PR-0360` added [REF-current-product-lanes-and-sir-convert-boundary-v1](ref-current-product-lanes-and-sir-convert-boundary-v1.md)

## Planning Boundary

This planning reference records intended direction and does not authorize implementation.

## Evidence Basis

The source evidence below remains the basis for the interpretation.

## Confirmed Contract

Only relationships and authority in candidate frontmatter are current.

## Backlog Derivation

Follow-up work remains in the linked backlog records.

## Planning Stop Conditions

Stop when authority, scope, or evidence is missing.

### Source evidence

### App Presentation Decomposition And Naming Plan

This reference is the durable output of `PR-0362` / `ST-37-04`. It turns the
current product-lane doctrine and service-shell plan into a PR-sized
implementation sequence for app names, descriptions, entrypoints, and future
decomposition work.

This package makes no code, route, registry, backend/API, Sir Convert, HuleEdu,
QTI, DOCX, public-capability, or Document Converter implementation changes.
Those changes remain gated by later reviewed PR slices.

### Governing Inputs

- `EPIC-37` is active and `REV-EPIC-37` is approved.
- `ST-37-04` owns app-presentation decomposition and naming.
- `PR-0360` added
  [REF-current-product-lanes-and-sir-convert-boundary-v1](ref-current-product-lanes-and-sir-convert-boundary-v1.md),
  which remains the authority for native-state versus heavy-conversion
  ownership.
- `PR-0361` added
  [REF-service-shell-ux-realignment-plan-v1](ref-service-shell-ux-realignment-plan-v1.md)
  and created the route-visible shell sequence `PR-0363` through `PR-0365`.

### Current Code Reality

| Surface | Current state | Planning consequence |
|---------|---------------|----------------------|
| `frontend/apps/skriptoteket/src/views/curatedAppHostRegistry.ts` | `classroom.group-seating-studio` has a bespoke host. `documents.conversion_hub` remains the shared backend/runtime host for authenticated Exam Converter fallback and the public Exam Converter host. | Klassrumskartan, Exam Converter, and Audio Transcription now have separate teacher-facing entrypoints while Exam/Audio still share technical backend authority. |
| `frontend/apps/skriptoteket/src/views/apps/ExamConverterAuthenticatedView.vue` | Canonical routes pass explicit `exam` or `transcript` presentation props. The generic `documents.conversion_hub` host ignores stale query residue and falls back to Exam Converter. | The old mode-query selector is no longer normal product routing. Shared runtime/auth plumbing remains centralized. |
| `frontend/apps/skriptoteket/src/router/routes.ts` | Authenticated `/apps/exam-converter` and `/apps/audio-transcription` exist before the generic `/apps/:appId` route. Public Exam Converter keeps `/public/apps/documents.conversion_hub/exam-converter`. | Canonical protected routes are query-free. The public Exam Converter route and shared backend app id remain unchanged. |
| `src/skriptoteket/infrastructure/curated_apps/registry.py` | The registry presents `documents.conversion_hub` as `Provhantering och ljudtranskribering` while keeping only the active `exam_converter` public capability. | Registry metadata is aligned to the shared technical runtime without creating a Document Converter route or public capability. |
| `frontend/apps/skriptoteket/src/views/HomeView.vue` and `frontend/apps/skriptoteket/src/components/layout/AuthSidebar.vue` | Authenticated home owns app entry; the persistent sidebar stays utility-first and does not duplicate app cards. | Home uses canonical app routes for runnable lanes and keeps Document Converter inert. |

`documents.conversion_hub` remains a technical backend/runtime id and public
Exam Converter namespace, not a teacher-facing product or mode-query selector.
Product copy and planning should not use "Conversion Hub" as a durable
teacher-facing concept unless it explicitly refers to historical compatibility
evidence.

### Lane Naming And Entrypoint Plan

The table below defines the canonical planning baseline for names,
descriptions, route/entrypoint impact, docs impact, and proof gates. It is a
naming/decomposition plan, not a copy lock. Final Swedish UI strings belong to
the copy-only follow-up slice.

| Lane | Canonical lane name | Description baseline | Truthful current entrypoint/status | Docs impact | Route and entrypoint implication | First proof gate |
|------|---------------------|----------------------|------------------------------------|-------------|----------------------------------|------------------|
| `classroom.group-seating-studio` | `Klassrumskartan` | Plan classrooms, groups, seating, rules, exports, and sharing in a native Skriptoteket workspace. | Authenticated `/apps/classroom.group-seating-studio`; public `/public/apps/classroom.group-seating-studio`. | Preserve the existing name across shell, help, and docs surfaces; no decomposition follow-up is needed beyond shell presentation updates. | Preserve the existing dedicated route family unless later reviewed shell work proves a change is needed. | If touched by shell work, use focused home/navigation tests plus browser proof for the changed Klassrumskartan entry. |
| `documents.conversion_hub` transcript runtime | `Audio Transcription` | Convert speech or media to saved transcript state, review speakers, and export transcript formats from Skriptoteket-owned transcript state. | Authenticated `/apps/audio-transcription`; current transcript fixture routes are dev/test surfaces. | Shell, help, and future docs may use the lane name. Technical docs should keep `documents.conversion_hub` only for shared backend/runtime authority and historical evidence. | `PR-0368` provided the separate teacher-facing transcript route; `PR-0374` removed the old mode-query selector. Shared runtime shell and backend logic remain reused. | Focused transcript presentation tests, `pdm run fe-type-check`, and authenticated HuleEdu shared-auth Docker plus Playwright proof for transcript submission, polling, replay/export, and protected route navigation. |
| `documents.conversion_hub` exam runtime | `Exam Converter` | Create exams, import exams, edit structure, items, points, answer keys, and metadata, review/correct answer-key state, export files, and grow toward native Skriptoteket sharing and QTI workflows after heavy import. | Authenticated `/apps/exam-converter`; public `/public/apps/documents.conversion_hub/exam-converter`; stale `/apps/documents.conversion_hub?mode=...` residue is ignored and falls back to the shared Exam Converter host. | Future docs and copy must describe creation, post-import correction, editing, sharing, and QTI growth as Skriptoteket-owned exam state rather than producer replay state. | `PR-0368` provided the separate teacher-facing Exam Converter route while preserving the public Exam Converter route and shared runtime shell/auth edge. | Focused exam presentation tests, existing Exam Converter route tests where relevant, `pdm run fe-type-check`, and authenticated HuleEdu shared-auth Docker plus Playwright proof for conversion, correction/replay, artifact download, and protected route navigation. |
| document lane | `Document Converter` | Convert and prepare PDF, DOCX, HTML/CSS, Markdown, and template-shaped presentation or document outputs. | Approved as a visible shell/app-shelf lane by the C2 mockup, but no truthful current route or runnable host has been proven yet. | Docs may describe this as an approved product lane, but runtime docs and links must not point to the current compatibility host unless a reviewed route-visible slice makes it truthful. | Do not route teachers to Exam Converter or Audio Transcription under a Document Converter label. A future route or app id needs its own reviewed route-visible slice and proof plan. | Browser proof is valid only after a truthful route target exists. If `PR-0364` reaches implementation without one, it must stop and attach/create the route-visible slice. |

### Change-Family Classification

| Change family | Included work | Explicit exclusions | PR-sized follow-up |
|---------------|---------------|---------------------|--------------------|
| Copy-only | Teacher-facing names, descriptions, headings, tabs, helper copy, and help text that can change without altering routes, app ids, registry records, or backend contracts. | No route alias, no registry metadata change, no backend/API contract change, and no Document Converter host. | `PR-0366` |
| Registry-only | `src/skriptoteket/infrastructure/curated_apps/registry.py` title/summary alignment and any bootstrap/fallback consumers that become truthful once shell copy is aligned. | No app-id split, no route change, no Sir Convert/HuleEdu/QTI/DOCX contract change, and no fake Document Converter implementation. | `PR-0367` |
| Route-visible | Canonical authenticated app entrypoints, authenticated home cards, authenticated navigation, and later dedicated teacher-facing route aliases or app-host headings if reviewed as necessary. | No backend/API decomposition unless the route-visible slice proves a concrete incompatibility; no replacement mode-query selector. | `PR-0363`, `PR-0364`, `PR-0365`, `PR-0368`, `PR-0374` |
| Backend/API-visible | New bootstrap semantics, public-capability changes, app-detail contract changes, generated types, or app-id decomposition only if route-visible work proves they are necessary. | No Sir Convert producer/Gateway boundary change, no HuleEdu contract change, no QTI/DOCX implementation, and no fake Document Converter implementation. | `PR-0369` |

### Auth Edge Preservation Invariant

Splitting the app identities is product-routing and presentation work, not an
auth rewrite or backend duplication. The authenticated Sir Convert edge must be
inventoried before implementation begins and kept under proof throughout the
cycle.

- Browser code must not construct or send `X-HuleEdu-Identity-*`, `X-API-Key`,
  bearer credentials, Sir Convert credentials, or browser-direct Sir Convert
  requests.
- `PR-0368` must not duplicate auth-edge handling per app identity. Exam
  Converter and Audio Transcription should reuse shared authenticated runtime
  shell/backend plumbing while presenting distinct teacher-facing app
  identities.
- HuleEdu Gateway remains responsible for browser session validation, CSRF,
  rate limiting, server-side Sir Convert key injection, signed
  `InternalIdentityContextV1`, route grants, and prefix stripping before
  Skriptoteket sees protected app traffic.
- The new Exam Converter and Audio Transcription app identities may share
  lower-level runtime clients, polling/idempotency helpers, artifact download
  code, formatter replay helpers, and shared shell infrastructure below the
  presentation boundary. They must not share a teacher-facing tab presentation.
- Conversion replay and artifact flows must preserve job id, correlation id,
  idempotency key, owner scope, artifact receipt, formatter replay, and signed
  identity assumptions exactly as proven by the current Gateway lane.
- Live proof for protected shell work must use the shared-auth Docker service
  lane and the existing Playwright/auth helpers. Direct cookie injection,
  credential POST shortcuts, host-only backend shortcuts, browser-authored
  identity headers, and browser-direct Sir Convert calls are invalid proof.

### Follow-Up PR Sequence

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
  split Exam Converter and Audio Transcription into separate route-visible
  teacher-facing app identities while reusing shared runtime shell/auth
  machinery and proving protected flows through the shared-auth
  Docker/Playwright lane.
- [PR-0369](../backlog/prs/pr-0369-st-37-04-backend-and-api-app-presentation-contract-alignment.md):
  proceed only if a reviewed route-visible slice proves that route or host
  decomposition cannot stay truthful without bootstrap or API-surface changes.
- [PR-0374](../backlog/prs/pr-0374-st-37-04-post-cutover-conversion-hub-compatibility-cleanup.md):
  removed the temporary `documents.conversion_hub?mode=...` compatibility path
  after the route-visible presentation cutover proved the separate app
  identities.
- [PR-0375](../backlog/prs/pr-0375-st-37-04-document-converter-backend-backed-mvp-planning.md):
  creates the separate Document Converter MVP planning package. It must review
  Sir Convert document-format contracts, backend/API needs, app-shell proof,
  artifact download/save/replay semantics, and auth-edge proof before any
  Document Converter route, host, registry capability, runtime link, or proof
  target is activated.
- [PR-0380](../backlog/prs/pr-0380-st-37-04-document-converter-product-contract-correction.md):
  corrects the Document Converter follow-up contract so simple lanes are
  app-boundary work inside Skriptoteket, Sir Convert is reserved for
  heavy/OCR/complex PDF paths, batch input is required, and route-visible UI is
  blocked behind mockup and copy approval.

### Sequencing Rules

1. `PR-0363` must land before any authenticated shell surface claims a direct
   Audio Transcription entrypoint.
2. `PR-0364` and `PR-0365` may present `Klassrumskartan`, `Audio
   Transcription`, `Exam Converter`, `Document Converter`, and
   `Kodredigerare` in the approved app hierarchy. Exam and transcript now use
   canonical query-free protected routes.
3. Document Converter may be visually present as the approved product lane, but
   runtime links must stop unless a reviewed truthful route target exists.
4. Copy-only name/description alignment should happen before registry metadata
   changes so route-visible shell surfaces establish the language first.
5. Registry metadata alignment should happen before any dedicated route alias or
   app-id decomposition, so bootstrap/catalog metadata does not keep advertising
   stale generic document-conversion copy.
6. `PR-0368` must begin with an auth-edge inventory and retained proof plan
   before editing route-visible app presentation.
7. Backend/API-visible changes are not authorized merely because the current
   technical app id is broad.
8. Compatibility routes may be retained during cutover only. `PR-0374` removed
   the mode-query presentation selector once the separate app identities were
   proven; do not add a replacement query, alias, or hidden selector.
9. Document Converter implementation must wait for `PR-0375`, the `PR-0380`
   correction, and their approved follow-up slices. Do not repurpose Exam
   Converter, Audio Transcription, public Exam Converter, or the generic
   backend app id as a document-conversion facade.

### Stop Conditions

- Stop if a proposed runtime change would label the current compatibility host,
  Exam Converter, Audio Transcription, catalog, or any generic fallback as
  Document Converter before a real document route exists.
- Stop if route-visible shell work weakens or bypasses the HuleEdu Gateway
  authenticated Sir Convert edge, including direct cookies, credential POSTs,
  browser-authored identity headers, host-only backend shortcuts, or
  browser-direct Sir Convert calls.
- Stop if route-visible work duplicates authenticated shell or auth-edge
  handling per app identity instead of reusing the shared runtime machinery.
- Stop if route-visible work tries to split app ids, public routes, registry
  semantics, or backend contracts without going through the later reviewed
  follow-up slices.
- Stop if an Exam Converter follow-up routes native exam state back into Sir
  Convert replay, hash, fingerprint, or artifact-overlay terminology after
  heavy import has completed.
- Stop if any implementation slice needs Sir Convert, HuleEdu, QTI, DOCX, or
  backend/API contract changes not named in its reviewed scope.

### Validation And Proof Expectations

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
