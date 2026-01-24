---
type: story
id: ST-14-36
title: "User file vault: reusable uploads + picker"
status: ready
owners: "agents"
created: 2026-01-12
updated: 2026-01-23
epic: "EPIC-14"
dependencies: ["ADR-0059", "ST-19-02"]
acceptance_criteria:
  - "Given a user has vault files, when they start a tool run, then they can select vault files instead of uploading new files (respecting input_schema file constraints)."
  - "Given a file-ref default (tool settings or action prefill) points to a vault file, when the run/action form renders, then the vault file is preselected if available; missing defaults block execution with an actionable validation error."
  - "Given vault files are selected, when the run executes, then the files are staged into /work/input and appear in the request manifest as normal inputs."
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
- Vault entries are created only via explicit user actions (e.g. “save upload”, “save run artifact”); tools must not
  auto-persist to vault.
- Vault file refs are valid defaults for tool settings and action prefill; the picker should honor defaults when
  available and surface a validation error when the referenced vault file is missing.

### Dependency alignment (no parallel mechanisms)

This story should treat vault files as a `FileRef` source (`vault:*`) and rely on ST-19-02 for:

- listing available vault file refs for the picker,
- validating access to selected vault refs,
- staging selected vault files into `/work/input/` for a run (no vault-specific staging path).
