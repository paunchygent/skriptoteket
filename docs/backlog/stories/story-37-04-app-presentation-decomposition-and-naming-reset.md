---
type: story
id: ST-37-04
title: "App presentation decomposition and naming reset"
status: ready
owners: "agents"
created: 2026-06-17
updated: 2026-06-18
epic: "EPIC-37"
dependencies:
  - "ST-37-01"
  - "ST-37-02"
  - "PR-0361"
  - "REF-current-product-lanes-and-sir-convert-boundary-v1"
  - "REF-service-shell-ux-realignment-plan-v1"
  - "EPIC-21"
acceptance_criteria:
  - "Given generic Conversion Hub presentation hides distinct teacher jobs, when app presentation is decomposed, then exam conversion/editor work, audio transcription, and general document conversion have separate names, descriptions, and entry surfaces."
  - "Given Exam Converter is a native app lane after heavy source import, when future QTI/edit/share workflows are presented, then they are described as Skriptoteket-owned exam state rather than Sir Convert replay state."
  - "Given document conversion is a separate lane, when it is presented, then it focuses on format conversion and template-shaped output such as PDF, DOCX, HTML/CSS, and platform-ready presentation artifacts."
  - "Given route or app registry changes are implemented, when the slice closes, then docs, generated types where relevant, frontend tests, and live browser proof all reflect the new app presentation."
ui_impact: "Yes (curated app registry, app cards/entrypoints, descriptions, and possibly routes)."
---

# ST-37-04: App Presentation Decomposition And Naming Reset

## Context

The product has grown from a generic Conversion Hub into several use-case
specific application lanes. Teachers should not have to infer whether "the
converter" means exam migration, speech-to-text, or document-format conversion.

This story owns the app-presentation reset after the backlog inventory and
dashboard direction are settled.

## Planned PR Slices

- [x] [PR-0362: ST-37-04 app presentation decomposition and naming package](../prs/pr-0362-st-37-04-app-presentation-decomposition-and-naming-package.md)
- [ ] [PR-0366: ST-37-04 copy-only app lane naming and description alignment](../prs/pr-0366-st-37-04-copy-only-app-lane-naming-and-description-alignment.md)
- [ ] [PR-0367: ST-37-04 curated app registry presentation alignment](../prs/pr-0367-st-37-04-curated-app-registry-presentation-alignment.md)
- [ ] [PR-0368: ST-37-04 route-visible app entrypoint and presentation alignment](../prs/pr-0368-st-37-04-route-visible-app-entrypoint-and-presentation-alignment.md)
- [ ] [PR-0369: ST-37-04 backend and API app presentation contract alignment](../prs/pr-0369-st-37-04-backend-and-api-app-presentation-contract-alignment.md)

## Notes

- The Exam Converter lane includes conversion, correction, future editing,
  sharing, QTI/source-neutral exam state, and later question-pool workflows.
- The Document Converter lane is separate and should speak to format and
  presentation output, not test/exam workflows.
- The Audio Transcription lane is separate from document conversion even when
  downstream transcript exports are document-like artifacts.
- Use
  [REF-current-product-lanes-and-sir-convert-boundary-v1](../../reference/ref-current-product-lanes-and-sir-convert-boundary-v1.md)
  as the ownership boundary before proposing names, descriptions, route impacts,
  or registry changes.
- `PR-0361` closed the service-shell planning package through
  [REF-service-shell-ux-realignment-plan-v1](../../reference/ref-service-shell-ux-realignment-plan-v1.md),
  and `PR-0362` closed the naming/decomposition planning package through
  [REF-app-presentation-decomposition-and-naming-plan-v1](../../reference/ref-app-presentation-decomposition-and-naming-plan-v1.md).
  `ST-37-04` remains open because the copy, registry, route-visible, and
  backend/API-visible implementation slices have not run.
