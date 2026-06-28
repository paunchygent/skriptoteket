---
type: pr
id: PR-0403
title: "ST-37-04 Document Converter preview touch-pinch ownership"
status: done
owners: "agents"
created: 2026-06-27
updated: 2026-06-28
stories:
  - "ST-37-04"
tags:
  - frontend
  - document-converter
  - touch
  - preview
dependencies:
  - "PR-0398"
  - "PR-0402"
  - "PR-0313"
acceptance_criteria:
  - "Given a teacher views a PDF preview on a touch screen, when they pinch on the preview surface, then Document Converter owns the gesture and changes the local preview zoom instead of allowing the browser/page to treat it as global page zoom."
  - "Given iPhone/Safari-style platform gesture events are dispatched on the preview target, when `gesturestart` and `gesturechange` occur, then the same local preview zoom path is used and browser default handling is prevented for the recognized gesture."
  - "Given a teacher uses one finger inside the PDF preview, when they pan/scroll, then normal one-finger preview panning remains available and is not blocked by the pinch handler."
  - "Given a teacher pinches over a visible document point, when preview scale changes, then the document remains anchored around the gesture midpoint rather than always growing from the top-left origin."
  - "Given the preview is in default fit-to-view mode or the teacher clicks `Anpassa till vyn`, when the document underfills one axis of the preview pane, then the document stays centered on the underfilled axis while still filling the available pane on the constrained axis."
  - "Given the retained proof runs, when it reports preview touch support, then it proves non-passive target binding/platform gesture ownership plus visible zoom-state change, not only fabricated Vue handler invocation."
  - "Given `HTML/CSS-projekt` mode renders on compact widths, when the source column already shows the categorized file lists, then the duplicated compact project summary panel above the dropzone is absent while the dropzone and categorized file lists remain."
---

# PR-0403: ST-37-04 Document Converter Preview Touch-Pinch Ownership

## Problem

`PR-0398` added PDF preview zoom controls and a touch-pinch handler, but
real-device testing shows the preview does not actually own the pinch gesture
on small/touch screens. Pinching over the document is being interpreted by the
browser/page as a global gesture instead of changing the local preview zoom.

This matches the earlier `PR-0313` classroom-map failure class: synthetic
`TouchEvent` tests can prove handler invocation while the real device still
routes the gesture to browser/native zoom before the app can prevent it.

## Goal

Make the Document Converter preview use the same durable gesture-ownership
shape that worked for the phone classroom map:

- bind the preview target with native non-passive listeners so recognized
  pinch gestures can call `preventDefault()`;
- support iPhone/Safari `gesturestart` / `gesturechange` / `gestureend` events
  in addition to ordinary two-touch movement;
- keep one-finger preview panning available;
- anchor preview zoom around the gesture midpoint so the document does not
  drift toward the top-left origin.

## Non-goals

- No new visual controls or labels.
- No broad rewrite of the Document Converter preview shell.
- No import of room/classroom domain semantics into Document Converter.
- No suppression of ordinary one-finger document panning.
- No production deploy, commit, or push unless separately requested.

## Implementation Plan

1. Add red-first focused tests that fail for the current preview because the
   target has no native non-passive/platform gesture binding.
2. Extract or adapt a small document-preview gesture owner modeled on
   `useRoomTouchViewportGestures`, keeping it domain-neutral to Document
   Converter.
3. Add anchored preview zoom compensation so the content coordinate under the
   gesture midpoint remains under that midpoint after scale changes.
4. Restore correct fit-to-view centering so the preview surface uses the
   available pane and does not stay left-biased when the document underfills
   one axis.
5. Wire `DocumentConverterResultPanel.vue` through target-ref binding instead
   of relying only on Vue template `@touch*` handlers.
6. Remove the duplicated compact project summary panel in `HTML/CSS-projekt`
   mode while keeping the source intake and categorized lists.
7. Extend the retained authenticated proof to verify the gesture ownership
   contract and visible preview zoom change.
8. Run focused frontend, browser, docs, and handoff validation, then submit the
   slice to retained review.

## Test Plan

- Focused red/green Vitest for Document Converter preview native non-passive
  target binding and platform `gesture*` support.
- Focused red/green Vitest for anchored preview zoom scroll compensation.
- Focused red/green Vitest for fit-mode centering when the preview underfills a
  wider pane.
- Focused red/green Vitest for absence of the duplicated compact project
  summary in `HTML/CSS-projekt` mode while the categorized source lists remain.
- Existing `DocumentConverterResultPanel` one-finger panning and pinch tests.
- Authenticated Document Converter browser proof through
  `scripts/authenticated_home_work_apps.py`, extended as needed to report the
  stronger preview touch-ownership contract.
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run fe-build`
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Progress

- Created this governed remediation slice after production touch testing showed
  browser/global pinch still wins over Document Converter preview zoom.
- Red-first frontend proof landed in
  `frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterResultPanel.spec.ts`:
  the new cases failed on the pre-fix route because the preview bound no native
  non-passive listeners, ignored `gesturestart` / `gesturechange`, and kept the
  pinch midpoint anchored to the top-left origin instead of compensating
  viewport scroll.
- Implemented a Document Converter-specific native gesture owner in
  `useDocumentPreviewTouchGestures.ts` plus anchored preview zoom in
  `useAnchoredDocumentPreviewZoom.ts`, keeping the route domain-neutral and
  reusing `useDocumentPreviewZoom.ts` only as the underlying scale model.
- Added a contained preview stage for fit mode so the PDF surface stays
  centered on the underfilled axis while still using the constrained viewport
  dimension for the default fit scale and `Anpassa till vyn`.
- Moved touch ownership from Vue template `@touch*` handlers to native
  non-passive target binding on the preview viewport and added Safari-style
  `gesture*` support.
- Made the embedded PDF iframe display-only with `pointer-events: none` so the
  scrollable preview viewport, not the browser PDF viewer, owns pinch/pan hit
  testing on real browser input.
- Removed the duplicated compact project summary panel from `HTML/CSS-projekt`
  mode while keeping the source dropzone and categorized HTML/CSS/image lists
  in the source rail.
- Repaired the shared-auth retained proof lane after the fit-stage change by
  trimming unrelated blocked-resource probes from
  `scripts/_document_converter_proof.py` so the real project-preview POST can
  finish through HuleEdu Gateway and reach the live fit/touch geometry checks.

## Verification Notes

- Red evidence:
  `pdm run fe-test -- --run frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterResultPanel.spec.ts`
  failed before the fix with four targeted regressions:
  no native non-passive target listeners, no platform `gesture*`
  `preventDefault()`/zoom path, no midpoint-anchored scroll compensation, and
  no fit-mode centering stage for underfilled previews.
- Focused green frontend evidence:
  `pdm run fe-test -- --run frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterResultPanel.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterView.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterProjectResult.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterSingleFileView.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterLayoutOwnership.spec.ts`
  passed with `29 passed`.
- Shared-auth proof red evidence after the fit-stage code landed:
  `pdm run python -m scripts.authenticated_home_work_apps --base-url http://127.0.0.1:5173`
  failed at `.artifacts/authenticated-home-work-apps/20260627T231319Z/` with
  `document-converter-preview-response.json` recording
  `502 EXTERNAL_SERVICE_ERROR` from HuleEdu Gateway while proxying the
  project-preview POST.
- Retained authenticated proof strengthening is partially implemented in
  `scripts/_document_converter_proof.py`: it now inspects native preview
  listener registration through Chromium CDP, records browser-level touch
  probe data separately from synthetic platform-gesture coverage, and now also
  checks fit-mode centering plus constrained-axis fill from live viewport
  geometry.
- Live authenticated proof green after the proof-lane fix:
  `pdm run python -m scripts.authenticated_home_work_apps --base-url http://127.0.0.1:5173`
  succeeded at `.artifacts/authenticated-home-work-apps/20260627T232025Z/`.
  The retained manifest records Chromium-CDP native non-passive listener
  coverage for `touchstart`/`touchmove`/`touchend`/`touchcancel` plus
  `gesturestart`/`gesturechange`/`gestureend`; native browser-level pinch zoom
  on the tablet viewport (`59% -> 119%`); platform-gesture zoom changes on
  desktop/tablet/compact (`55% -> 63%`, `119% -> 137%`, `37% -> 43%`);
  one-finger scrolling preserved (`one_finger_move_prevented: false`); and
  contained fit geometry with constrained-axis fill plus centered underfill
  (`desktop left/right inset 2.06px/2.06px`, `tablet 0.17px/0.19px`,
  `compact 0.52px/0.53px`).
- Earlier reruns briefly hit HuleEdu login `RATE_LIMIT` while iterating on the
  strengthened proof; the last rate-limit artifact root was
  `.artifacts/authenticated-home-work-apps/20260627T175912Z/`.
