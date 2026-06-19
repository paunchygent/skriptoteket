---
type: story
id: ST-14-36
title: "User file vault: reusable uploads + picker"
status: done
owners: "agents"
created: 2026-01-12
updated: 2026-06-18
epic: "EPIC-14"
dependencies: ["ADR-0059", "ST-19-02", "ST-14-24"]
acceptance_criteria:
  - "Given a user has vault files, when they start a tool run, then they can select vault files per file field instead of uploading new files (multiple file fields supported; respecting min/max constraints per field)."
  - "Given a file-ref default (tool settings or action prefill) points to a vault file, when the run/action form renders, then the vault file is preselected if available; missing defaults block execution with an actionable validation error."
  - "Given vault files are selected, when the run executes, then the files are staged into /work/input and appear in the request manifest as normal inputs with field ownership preserved."
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

- Action-form selection of vault files uses the same file-field contract as ST-14-24 (first-class file references).
- Vault entries are created only via explicit user actions (e.g. “save upload”, “save run artifact”); tools must not
  auto-persist to vault.
- Vault file refs are valid defaults for tool settings and action prefill; the picker should honor defaults when
  available and surface a validation error when the referenced vault file is missing.

## Decisions (LOCKED)

- **Value shape is always list:** file field values MUST be `FileRef[]` (array), even when max=1.
- **Multiple file fields are REQUIRED:** run/action forms MUST support more than one file field and preserve per-field
  mapping throughout request → staging → manifest.
- **Save-to-vault is explicit:** saving to vault MUST be user-initiated (no auto-save).
- **Vault management UX is REQUIRED:** the vault UI MUST support active list + soft-deleted “papperskorg” with
  delete/restore, plus:
  - search by filename
  - sorting: Newest, Name (A–Ö), Size
  - a visible quota/usage bar (e.g. `x MB / y MB`) and actionable limit messaging

### Dependency alignment (no parallel mechanisms)

This story should treat vault files as a `FileRef` source (`vault:*`) and rely on ST-19-02 for:

- listing available vault file refs for the picker,
- validating access to selected vault refs,
- staging selected vault files into `/work/input/` for a run (no vault-specific staging path).

## Implementation Summary (as of 2026-06-18)

- The user vault ships in the current repo through `/api/v1/vault`,
  `VaultPanel.vue`, `VaultPickerModal.vue`, `useVaultFiles.ts`,
  `LocalVaultStorage`, the vault repositories/handlers, and `vault:*`
  file-ref resolution.
- Current surfaces cover explicit save-to-vault, soft delete, restore,
  retention-aware management, quota display, picker defaults, and owner-scoped
  access, so `PR-0359` repairs this story to `done`.
