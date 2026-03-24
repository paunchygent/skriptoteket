---
type: story
id: ST-26-01
title: "Klassrumskartan — Seating PDF poster export with standalone renderer"
status: done
owners: "agents"
created: 2026-03-24
epic: "EPIC-26"
dependencies: ["ADR-0069", "ADR-0071", "ADR-0072", "EPIC-24"]
acceptance_criteria:
  - "Given a teacher exports the current seating draft, when the export completes, then Skriptoteket returns a one-page PDF artifact rendered from a standalone seating-poster renderer rather than from live planner DOM or print CSS."
  - "Given a seating export request is created, when the backend receives it, then the request identifies the target draft explicitly by `seatingDraftId` rather than resolving an implicit current draft server-side."
  - "Given the exported seating PDF uses the first approved layout, when it renders, then it uses `pretty_brutalist_poster` with strong room geometry, high contrast, large student labels, and light branding only."
  - "Given PDF artifact generation runs for seating export, when the conversion step is executed, then Skriptoteket delegates the final document conversion/rendering through the dedicated Sir Convert-a-Lot service boundary rather than introducing a planner-owned generic PDF engine path."
  - "Given the seating poster is prepared for PDF conversion, when intermediate render input is produced, then the canonical source is export-specific HTML/CSS rather than planner DOM reuse, screenshot export, or direct PDF drawing primitives."
  - "Given the teacher prints the seating PDF, when it is viewed at classroom distance, then student names and seat placements remain legible and the room orientation remains easy to understand."
  - "Given the current seating draft has room fixtures and seating geometry, when the PDF is rendered, then the artifact reflects the same classroom scene model rather than an ad hoc duplicate geometry contract, including whiteboard, teacher desk, door, windows, benches, and tables where present."
  - "Given student labels are rendered on the poster, when names are formatted, then the canonical poster label is `first name + last initial` with no alternate fallback format."
  - "Given the first export story ships, when the teacher opens the export action, then only the approved seating poster layout is offered and no low-value metadata page or bundled legend page is produced."
ui_impact: "Yes (new seating export action and download flow)"
data_impact: "Yes (explicit seating export artifact contract)"
---

## Context

EPIC-24 established the class-first seating workflow and explicitly deferred durable artifacts to a later export flow. The first export story should solve the highest-value teacher use case: a seating poster that can be printed and placed on the whiteboard.

## Notes

- Do not implement this as a print stylesheet for the live planner UI.
- Build a dedicated export presentation model from the seating draft plus room geometry.
- Keep the artifact one-page and whiteboard-focused.
- Do not add extra PDF pages for roster legends, notes, timestamps, or similar filler.
- The canonical intermediate render source is export-specific HTML/CSS.
- The export request should identify the target seating draft explicitly by `seatingDraftId`.
- Poster labels use one canonical format only: `first name + last initial`.
- Required room markers include whiteboard, teacher desk if present, door if present, windows if present, and benches/tables if present.
- The renderer contract should be layout-ready from the start, but only `pretty_brutalist_poster` ships in this story.
- Prefer the Hule internal-network Sir Convert-a-Lot lane where available; do not make public internet routing the primary planning assumption.
