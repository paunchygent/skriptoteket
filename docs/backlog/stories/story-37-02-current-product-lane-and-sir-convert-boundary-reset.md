---
type: story
id: ST-37-02
title: "Current product lane and Sir Convert boundary reset"
status: done
owners: "agents"
created: 2026-06-17
updated: 2026-06-18
epic: "EPIC-37"
dependencies:
  - "ST-37-01"
  - "REF-current-product-direction-and-backlog-inventory-2026-06-17"
acceptance_criteria:
  - "Given the app has evolved beyond generic script running, when current product direction is documented, then the durable docs name Klassrumskartan, audio transcription, Exam Converter, and general Document Converter as separate teacher-facing application lanes."
  - "Given Sir Convert-a-Lot owns heavy conversion and model/runtime work, when app workflows are planned, then lightweight transcript, exam, QTI, sharing, and editing state remains owned by Skriptoteket instead of being routed through unnecessary replay or fingerprint workflows."
  - "Given legacy script/editor work remains valuable, when product-lane docs are updated, then they preserve the editor/runner as aligned platform capabilities rather than front-door value copy."
---

# ST-37-02: Current Product Lane And Sir Convert Boundary Reset

## Context

Conversion Hub and the historical tool catalog still carry broad labels that no
longer describe how teachers experience the product. The next product framing
needs to be lane-specific and honest:

- classroom planning in Klassrumskartan
- speech or media to transcript
- exam conversion, correction, editing, sharing, and future QTI/source-neutral
  exam-state workflows
- general document conversion and presentation-format output

This story turns the direction into durable docs before app names, descriptions,
or shell routes are changed.

## Planned PR Slice

- [x] [PR-0360: ST-37-02 current product lane and Sir Convert boundary reference](../prs/pr-0360-st-37-02-current-product-lane-and-sir-convert-boundary-reference.md)

## Notes

- The boundary must be explicit: Sir Convert-a-Lot handles heavy conversion,
  hosted model inference, and producer-owned artifacts. Skriptoteket handles
  saved app state, teacher review, editing, sharing, and file actions once the
  native product state exists.
- Future DOCX, QTI editor, and question-pool work should build on this boundary
  rather than treating Sir Convert replay as the default state engine.

## Implementation Summary

Completed on 2026-06-18 through
[PR-0360](../prs/pr-0360-st-37-02-current-product-lane-and-sir-convert-boundary-reference.md).
The durable reference
[REF-current-product-lanes-and-sir-convert-boundary-v1](../../reference/ref-current-product-lanes-and-sir-convert-boundary-v1.md)
now defines the current teacher-facing lanes, the Sir Convert heavy-conversion
boundary, the Skriptoteket native-state boundary, and the preserved
script/editor/runner capability. `EPIC-37` remains proposed until
`REV-EPIC-37` is approved.
