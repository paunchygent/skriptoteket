---
type: story
id: ST-14-36
title: "User file vault: reusable uploads + picker"
status: ready
owners: "agents"
created: 2026-01-12
epic: "EPIC-14"
dependencies: ["ADR-0059"]
acceptance_criteria:
  - "Given a user has vault files, when they start a tool run, then they can select vault files instead of uploading new files (respecting input_schema file constraints)."
  - "Given vault files are selected, when the run executes, then the files are staged into /work/input and appear in the input manifest as normal inputs."
  - "Given a user saves a run artifact to the vault, when they confirm, then the artifact is copied into the vault and appears in the picker."
  - "Given a user deletes a vault file, when they confirm, then it is soft-deleted (hidden from the picker) and does not delete historical runs or artifacts."
  - "Given a user restores a soft-deleted vault file within the retention window, when they confirm, then it reappears in the picker."
  - "Given a vault file has been soft-deleted past the retention window, when cleanup runs, then it is permanently removed."
  - "Given a user is not the owner, when they attempt to access a vault file, then access is denied."
  - "Given storage or retention limits are exceeded, when saving to the vault, then the UI shows an actionable validation error."
ui_impact: "Yes (tool run file picker)"
data_impact: "Yes (new file vault persistence)"
---

## Context

Many tools rely on repeated uploads of the same files. A per-user file vault reduces friction and enables reuse.

## Notes

- Action-form selection of vault files can be added later with ST-14-24 (first-class file references).
- Vault entries can be created from explicit “save upload” actions; artifact-to-vault saving can be a follow-up.
