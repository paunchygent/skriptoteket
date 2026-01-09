---
type: story
id: ST-14-32
title: "Editor: cohesion pass (panel language + input selectors across modes)"
status: in_progress
owners: "agents"
created: 2026-01-09
updated: 2026-01-09
epic: "EPIC-14"
acceptance_criteria:
  - "Given the author switches between Källkod/Diff/Metadata/Testkör, then typography, spacing, borders, and button sizes stay consistent (IDE-like, no drawer-style headers inside the editor surface)."
  - "Given the editor shows input selectors (preset/entrypoint/diff target), then they share one compact size system (height, font, padding) and one tooltip/help pattern without label collisions."
  - "Given the author interacts with Testkör mode, then in-editor actions (file picker, run, clear) use the same editor utility hierarchy (no large CTA-style buttons inside the editor)."
  - "Given the author uses Metadata mode, then the panel uses the same compact section headers and actions as the main editor (no redundant intro copy)."
  - "Given the author uses Diff mode, then diff controls use the same utility button + select styling as the rest of the editor."
dependencies:
  - "PR-0011"
ui_impact: "Yes (editor modes + Testkör/Metadata/Diff UI cohesion)"
data_impact: "No"
---

## Context

The editor shell is now stable (fixed-height, mode toggles, chat column), but non-source modes still look and feel like
embedded drawers/pages. This story aligns **all editor modes** to a single compact "editor panel language" so the editor
reads as one coherent IDE surface.

## Notes

- This is a **design cohesion** pass; avoid changing behavior/contracts unless required for consistency or accessibility.
- Prioritize small, reusable primitives over one-off styling.
