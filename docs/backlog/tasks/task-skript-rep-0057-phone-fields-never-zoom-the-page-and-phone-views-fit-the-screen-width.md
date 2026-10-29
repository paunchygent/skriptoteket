---
type: task
id: TASK-SKRIPT-REP-0057
title: Phone fields never zoom the page and phone views fit the screen width
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-29'
status: ready
closeout_review:
  record: inline
  status: not_started
task_kind: repository
acceptance_criteria:
  - On touch devices every input, select and textarea in the app shows text of at least 16 px, so tapping a field never zooms the page
  - 'At phone width (390 px) no view is wider than the screen: the page scrolls only vertically and wide content scrolls inside its own container'
  - Teachers can still pinch-zoom the page on purpose; the viewport meta does not lock zoom
  - 'On phone layouts a row of action buttons never wraps onto a second row; Klassrumskartan''s "Redigera klasslista" dialog footer shows Radera, Avbryt and Spara in one row at 390 px'
backlog_document_profile: contract-derived
---

## Implementation Contract

On a phone, tapping an input zooms the page (iOS WebKit zooms on focus when field text is under 16 px; every
iPhone browser, Chrome included, uses WebKit) and the page does not zoom back when the field loses focus. The
teacher must then pinch the whole page back. Some phone views are also wider than the screen, so the page
scrolls sideways. Both break phone use across the app.

- Actor: any signed-in teacher or guest using Skriptoteket on a phone.
- Change 1: on touch devices (`(pointer: coarse)` or `(hover: none)`) every input, select and textarea in the
  SPA and curated apps uses text of at least 16 px. Set it once in the shared field styles; remove local
  overrides that go below 16 px on touch.
- Change 2: at 390 px width no view overflows horizontally. Wide content (tables, maps, toolbars) scrolls
  inside its own container; the page body scrolls only vertically. Fix each overflowing view at its cause; no
  global `overflow-x: hidden` on `html` or `body` that hides content.
- The viewport meta stays without `maximum-scale` or `user-scalable=no`: teachers can still pinch-zoom the
  page on purpose.
- Change 3: on phone layouts a row of action buttons never wraps onto a second row. The case seen on the user's
  iPhone is the "Redigera klasslista" dialog footer in Klassrumskartan, where Radera stands alone and Avbryt and
  Spara drop below it. Fix every dialog footer and action row that wraps this way at its shared cause, as
  `huleedu-ui-design` directs: a delete action is its delete glyph alone (`UiDenseIconButton tone="danger"`),
  actions stay in one row, and at the narrowest width a label is shortened and a glyph carries the meaning.
- Non-goals: desktop field sizes, canvas pinch behaviour (TASK-SKRIPT-27-09-05), redesign of any view.

## Contract Inputs

- User report and decisions 2026-10-29 in the Hemma orchestrator session (AskUserQuestion: 16 px fields on
  touch, whole app).
- `frontend/apps/skriptoteket/index.html` viewport meta; shared field styles in the frontend workspace;
  `huleedu-ui-design` (typography, dense workspaces, phone layout).

## Core Vertical And Performance

The core vertical is one phone view: tap a field, no zoom; the view fits 390 px. Units for juniors:

1. Shared field styles: 16 px minimum text for input, select and textarea on touch; remove smaller touch
   overrides found by search.
2. Width audit: list every route and curated-app view that overflows at 390 px (measured, e.g.
   `document.documentElement.scrollWidth > innerWidth`), then fix each at its cause, one junior per group of
   views.

No runtime cost beyond CSS.

## Validation

- A focused Vitest or CSS check that the touch field rule exists and no touch override sets field text
  below 16 px.
- A Mac staging walk at 390x844 with touch emulation: tap a field in each main view, no page zoom (computed
  field font size at least 16 px); `scrollWidth` equals `innerWidth` on every audited view.
- The user taps fields on their iPhone after the production deploy.

## Stop Conditions

- A view needs a layout redesign, not a fix, to fit 390 px: list it and stop for a decision.
- A shared design-system package owns the field styles and cannot be changed from this repository.

## Decided Contract Terms

| ID  | Decided contract term                                                                                       |
| --- | ----------------------------------------------------------------------------------------------------------- |
| D1  | Touch fields use text of at least 16 px so iOS never zooms on focus (user decision 2026-10-29).             |
| D2  | Page pinch-zoom stays allowed; the viewport meta is not locked (user decision 2026-10-29).                  |
| D3  | Scope is the whole app: shared field styles and every phone view (user decision 2026-10-29).                |
| D4  | Overflow is fixed at each cause; wide content scrolls in its own container; no global overflow clipping.    |
| D5  | Proof is focused tests, one Mac staging walk at 390x844 and the user's iPhone check; light lead, no review. |
| D6  | On phone layouts a row of action buttons never wraps onto a second row (user decision 2026-10-29).          |
