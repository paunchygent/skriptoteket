---
type: epic
id: EPIC-26
title: "Klassrumskartan — explicit exports and class-list import"
status: active
owners: "agents"
created: 2026-03-24
updated: 2026-03-24
outcome: "Teachers can export Klassrumskartan seating plans as a poster-grade standalone PDF, import class lists from common teacher files with confirmation before save, export seating as editable XLSX, and later export grouping layouts through separate artifacts without conflating draft autosave or undo/redo history with teacher-facing saved outputs."
dependencies: ["ADR-0069", "ADR-0071", "ADR-0072", "EPIC-24"]
---

## Scope

- Introduce explicit teacher-facing export artifacts as the next Klassrumskartan lane after EPIC-24.
- Keep exports separate from autosave, draft continuity, and bounded undo/redo history.
- Ship seating exports before grouping exports.
- Treat the seating PDF as a standalone print renderer, not as a print stylesheet over the live planner UI.
- Prefer Sir Convert-a-Lot as the dedicated conversion/export service where that keeps Klassrumskartan aligned with SRP and existing platform seams.
- Start with one seating PDF layout:
  - `pretty_brutalist_poster`
- Make the export contract layout-ready from the start so later stories can add teacher-selectable layouts without rewriting the renderer contract.
- Keep the seating PDF artifact focused on one-page whiteboard-friendly readability:
  - strong room geometry
  - large, legible student names
  - light branding only
  - no low-value metadata clutter
- Add bounded class-list import as the same teacher I/O lane:
  - `XLSX` as the primary structured import
  - `TXT` as a lightweight fallback
  - `PDF` parsed through Sir Convert-a-Lot using the fast parsing lane rather than the heavier default path
- Require teacher preview and confirmation before imported students or class names are saved.
- Prefer Hule internal-network service routing for Sir Convert-a-Lot in planning and implementation where available, with public/external access treated as a fallback rather than the primary lane.
- Follow seating exports with editable seating `XLSX`.
- Follow seating exports with separate grouping export artifacts:
  - grouping PDF
  - grouping XLSX

## Out of scope

- Reopening EPIC-24 for new feature work.
- Treating ordinary draft autosave or undo/redo state as teacher-facing export/checkpoint artifacts.
- Advanced teacher-facing checkpoint/history UX beyond the minimal explicit export contract.
- Student metadata expansion beyond what class-list import strictly needs to create or update a class roster.
- Zoning, smart placement, pair rules, weighting, or assignment intelligence.
- Reusing live planner CSS, DOM, or screenshots as the export implementation.
- Shipping multiple seating PDF layouts in the first export story.
- `DOCX` export in this epic unless a later approved story explicitly adds it.

## Risks

- A weak export renderer contract could accidentally couple artifact quality to current SPA layout constraints.
- PDF import could become over-scoped if it tries to perfectly understand arbitrary school documents instead of staying preview-first and teacher-confirmed.
- Grouping exports could drift into seating-first assumptions if the artifact models are not kept separate.

## Stories

- [x] [ST-26-01: Seating PDF poster export with standalone renderer](../stories/story-26-01-klassrumskartan-seating-pdf-poster-export-with-standalone-renderer.md)
- [ ] [ST-26-02: Class-list import from file with teacher preview and confirmation](../stories/story-26-02-klassrumskartan-class-list-import-from-file-with-preview-and-confirmation.md)
- [ ] [ST-26-03: Seating XLSX export](../stories/story-26-03-klassrumskartan-seating-xlsx-export.md)
- [ ] [ST-26-04: Grouping PDF export](../stories/story-26-04-klassrumskartan-grouping-pdf-export.md)
- [ ] [ST-26-05: Grouping XLSX export](../stories/story-26-05-klassrumskartan-grouping-xlsx-export.md)

## Implementation Summary (as of 2026-03-24)

- `ST-26-01` is implemented locally through `PR-0118` and `PR-0119`.
- Seating exports now have an explicit prepare-contract seam plus an async PDF
  export-job lane with standalone poster-scene translation, export-owned
  HTML/CSS rendering, Sir Convert-a-Lot delivery, Vault persistence, and typed
  status/download routes.

## Notes

- This epic follows the accepted EPIC-24 direction that durable artifacts come later through explicit export rather than ordinary save.
- The first shipped export artifact is intentionally “no slop”:
  - one page
  - poster-grade
  - readable at distance
  - no second-page filler
- Editable/tabular needs belong to `XLSX`, not to extra PDF pages.
- PDF import should use the existing Sir Convert-a-Lot service model rather than introducing a bespoke heavy parsing lane inside Klassrumskartan itself.
- PDF and document export planning should prefer the dedicated Sir Convert-a-Lot service boundary rather than folding conversion concerns into planner-owned rendering/runtime responsibilities.
- A review doc should be created and approved before implementation begins, per the repo review workflow.
