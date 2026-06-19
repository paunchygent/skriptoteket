---
type: reference
id: REF-service-shell-ux-realignment-plan-v1
title: "Service shell UX realignment plan"
status: active
owners: "agents"
created: 2026-06-18
topic: "service-shell-ux-realignment"
---

# Service Shell UX Realignment Plan

This reference is the durable output of `PR-0361` / `ST-37-03`. It turns the
approved `EPIC-37` direction into a PR-sized implementation sequence for the
authenticated service shell and dashboard.

No UI code, route names, app ids, registry names, or Sir Convert contracts are
changed by this reference. Route-visible implementation work must happen in the
follow-up PR slices listed below and must pass the review gate before code
changes begin.

## Governing Inputs

- `EPIC-37` is active and `REV-EPIC-37` is approved.
- `ST-37-01` repaired stale backlog state through `PR-0358` and `PR-0359`.
- `ST-37-02` created
  [REF-current-product-lanes-and-sir-convert-boundary-v1](ref-current-product-lanes-and-sir-convert-boundary-v1.md).
- The current teacher-facing lanes are `Klassrumskartan`, `Audio
  Transcription`, `Exam Converter`, and `Document Converter` as the approved
  document-conversion product lane. `Document Converter` still needs a
  truthful route target before runtime implementation can link it.
- `Kodredigerare` is a first-class app surface in the authenticated shell, not
  a secondary form or suggestion card.
- Vault/files, catalog, suggestions, and owned-tool management remain valuable
  secondary surfaces. `Mina körningar`, latest-used rows, and recent-used
  vanity chrome are no longer part of the authenticated home direction.

## Current Code Reality

| Surface | Current state | Planning implication |
|---------|---------------|----------------------|
| `frontend/apps/skriptoteket/src/views/HomeView.vue` | Signed-out users see a Klassrumskartan-focused landing surface. Signed-in users see greeting, favorites, recent tools, run history, catalog, contributor, editor, suggestion, and admin cards. | The signed-in home needs the approved app shelf first and should remove run/latest/recent vanity chrome from the home surface. |
| `frontend/apps/skriptoteket/src/composables/home/useHomeDashboard.ts` | Loads runs, favorites, recent tools, contributor tools, and admin review counts. | The data may remain for other routes or future work, but `PR-0364` should not render runs/latest/recent as authenticated home chrome. |
| `frontend/apps/skriptoteket/src/components/layout/AuthSidebar.vue` | Navigation leads with `Hem`, `Profil`, `Katalog`, `Mina körningar`, `Mina filer`, and role-gated tool/admin links. | The navigation should gain app-first structure after the home surface establishes the lane model. |
| `frontend/apps/skriptoteket/src/views/curatedAppHostRegistry.ts` | `classroom.group-seating-studio` has a bespoke host. `documents.conversion_hub` opens the authenticated Exam Converter view and public Exam Converter view. | Do not split app ids here. Use current app ids until `ST-37-04` decides app presentation decomposition. |
| `frontend/apps/skriptoteket/src/views/apps/ExamConverterAuthenticatedView.vue` | Owns a local `activeHubMode` between `exam` and `transcript`; the URL does not currently deep-link to transcript mode. | Add a small mode-deep-link contract before the home can truthfully link to Audio Transcription. |
| `src/skriptoteket/infrastructure/curated_apps/registry.py` | Registry title for `documents.conversion_hub` is still `Konvertera dokument`, but the active bespoke host currently presents Exam Converter plus transcript mode. | Registry naming belongs to `ST-37-04`; the shell must not route the approved Document Converter lane to Exam/Transcript under a false label. |

## Closed Scope Decisions

| Decision | Source | Result |
|----------|--------|--------|
| Front-door focus shifts from script-first/tool-first to teacher app lanes. | `EPIC-37`, `REF-current-product-lanes-and-sir-convert-boundary-v1` | Authenticated home should lead with productivity apps. |
| Script/editor capability remains valuable. | `EPIC-37`, `REF-current-product-direction-and-backlog-inventory-2026-06-17`, approved C2 mockup | Present `Kodredigerare` as a first-class app shelf. Do not use `Mina körningar` as home chrome. |
| Sir Convert owns heavy conversion; Skriptoteket owns native app state and presentation. | `REF-current-product-lanes-and-sir-convert-boundary-v1` | Shell work must not route native app state back through Sir Convert replay/fingerprint workflows. |
| No route/app-id rename in `PR-0361`. | `PR-0361` non-goals | Follow-up code may add query state or entry links, but app-id decomposition waits for `ST-37-04`. |
| Protected route proof must use HuleEdu browser-session ceremony. | `AGENTS.md`, integrated frontend stack, `.codex/rules/075-browser-automation.md` | Every route-visible implementation slice needs focused Vitest/typecheck plus live authenticated browser proof. |

## Assumptions And Recommendations

| Question | Options | Recommendation |
|----------|---------|----------------|
| How should the shell expose Exam Converter and Audio Transcription before app-id decomposition? | A: add `?mode=exam/transcript` deep links on the existing `documents.conversion_hub` route. B: split routes/app ids now. C: keep one generic entry until `ST-37-04`. | Choose A. It gives truthful direct shell entrypoints without doing the naming/decomposition work early. |
| How should Document Converter appear before a real implementation lane exists? | A: show it in the approved app shelf only if a truthful reviewed route target exists. B: stop and create/attach the required route-visible slice. C: link it to current `documents.conversion_hub` or catalog. | Choose A only when route truth is available; otherwise B. Reject C. |
| Should favorites/recent/runs remain above app lanes? | A: keep current order. B: move app lanes first and preserve favorites/recent/runs below. C: remove run/latest/recent vanity chrome from home. | Choose C for `PR-0364`; `Mina filer` remains the important continuation path. |
| Should shell navigation be changed before home content? | A: change sidebar first. B: change home first, then sidebar. C: wait for all app decomposition. | Choose B unless the user explicitly merges `PR-0364` and `PR-0365`. The approved C2 mockup is the shared target. |

No remaining product decision blocks the planning package. The future
implementation blockers are review approval for each implementation PR and the
`ST-37-04` naming/decomposition package before app presentation labels are
changed.

The implementation PRs below are therefore documented now but remain blocked
until `PR-0362` closes.

## Implementation Sequence

### 1. `PR-0363`: Conversion Lane Mode Deep-Link Contract

Add a route-query contract for the current `documents.conversion_hub`
authenticated host so shell links can open either Exam Converter or Audio
Transcription without renaming the app id.

Expected first red proof:

- `pdm run fe-test -- --run src/views/apps/ExamConverterAuthenticatedView.spec.ts src/router/routes.spec.ts`
- The new test should fail because `/apps/documents.conversion_hub?mode=transcript`
  currently defaults to Exam Converter.

Required green proof:

- Focused Vitest proves `mode=exam`, `mode=transcript`, invalid mode fallback,
  and tab-to-query synchronization.
- `pdm run fe-type-check`.
- Authenticated browser proof reaches both mode-specific entries through the
  sanctioned HuleEdu ceremony.

### 2. `PR-0364`: Authenticated Home Work-Apps Surface

Replace the signed-in dashboard's first impression with the approved C2 primary
work-app shelf while preserving files/catalog/contribution affordances below it.

Expected first red proof:

- `pdm run fe-test -- --run src/views/HomeView.spec.ts`
- The new authenticated-home test should fail because the current signed-in home
  leads with favorites/recent/runs/tools instead of app-lane entrypoints.

Required green proof:

- Focused HomeView/component tests prove app lanes appear first,
  `Kodredigerare` is a primary app, `Mina körningar`/latest/recent chrome is
  absent, secondary affordances are not nested cards, contributor/admin gates
  remain intact, and Document Converter is not routed falsely.
- `pdm run fe-type-check`.
- Browser proof covers authenticated `/` at desktop and compact widths.

### 3. `PR-0365`: Authenticated Shell Navigation Realignment

Update the authenticated sidebar/mobile drawer/top-shell navigation to match
the app-first home hierarchy after the home surface has established the lane
model.

Expected first red proof:

- `pdm run fe-test -- --run src/components/layout/AuthLayout.spec.ts src/App.spec.ts`
- The new test should fail because the current sidebar leads with generic
  catalog/tool navigation and has no primary app-lane section.

Required green proof:

- Focused layout tests prove app links are primary, platform/tool/admin links
  stay role-gated, focus mode and immersive game mode remain unchanged, and
  Klassrumskartan's wider sidebar breakpoint still holds.
- `pdm run fe-type-check`.
- Browser proof covers desktop sidebar and mobile drawer through the HuleEdu
  browser-session path with no overlap or text clipping.

## Stop Conditions

- Stop and return to planning if implementation needs route/app-id renames,
  registry decomposition, or new public app contracts before `ST-37-04` closes.
- Stop if a proposed Document Converter entry would send teachers to Exam
  Converter, transcript mode, catalog, or the current compatibility host
  without a truthful reviewed route.
- Stop if an implementation requires Sir Convert, HuleEdu Gateway, QTI, DOCX,
  or backend API contract changes not named in the PR slice.
- Stop if browser proof cannot use the HuleEdu ceremony and repo helpers.

## Close-Out Gates For Future Route-Visible PRs

- Focused Vitest for changed component/route behavior.
- `pdm run fe-type-check`.
- `pdm run docs-validate`.
- `pdm run handoff-validate` when `.codex/handoff.md` is updated.
- `git diff --check`.
- Live browser proof through the sanctioned HuleEdu browser-session ceremony,
  with retained artifacts named in `.codex/handoff.md`.
