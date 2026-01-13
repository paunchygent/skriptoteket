---
type: story
id: ST-14-35
title: "Tool datasets: per-user CRUD + picker"
status: ready
owners: "agents"
created: 2026-01-12
epic: "EPIC-14"
dependencies: ["ADR-0058"]
acceptance_criteria:
  - "Given a user has datasets for a tool, when they open the tool run view, then a dataset picker lists their datasets and allows selecting one for the run."
  - "Given a user saves a dataset with a name and payload, when they submit, then it is stored per user+tool and appears in the picker."
  - "Given a user edits or deletes a dataset, when they confirm, then the change is persisted and does not affect other users."
  - "Given a dataset is selected, when a run starts, then the runner receives it in memory per ADR-0058 (dataset + dataset_meta)."
  - "Given a dataset payload exceeds size limits or is invalid JSON, when saving, then the UI shows an actionable validation error."
ui_impact: "Yes (tool run dataset picker + management UI)"
data_impact: "Yes (new dataset persistence)"
---

## Context

Tools like group generators need reusable, per-user lists (classes, rosters, templates). Settings alone are not enough.

## Notes

- Integrate with the "settings suggestions" UX (ST-14-34) once available so tools can propose dataset saves.
- Keep dataset selection optional; tools must handle `memory["dataset"]` missing.
