---
type: pr
id: PR-0055
title: "User file vault: UI picker + defaults"
status: done
owners: "agents"
created: 2026-01-24
updated: 2026-06-18
stories:
  - "ST-14-36"
tags: ["frontend"]
acceptance_criteria:
  - "Vault files appear in run/action pickers per file field (multiple file fields supported) and respect file constraints."
  - "File field values are always FileRef[] (array), even when max=1."
  - "Vault defaults preselect when available; missing defaults block execution with an actionable validation error."
  - "Users can save artifacts to vault from ToolRunArtifacts; users can delete/restore vault entries from the vault UI."
---

## Problem

ST-14-36 needs a user-facing picker for vault files, plus default preselect behavior and validation. Without a UI,
vault refs are not actionable.

Parent: EPIC-14. Depends on PR-0054 backend endpoints and PR-0053 UI contract behavior.

## Goal

Deliver the vault picker UI for runs/actions, handle defaults, and support save/delete/restore flows with clear UX.

## Decisions (LOCKED)

- **Multiple file fields are REQUIRED:** the UI MUST render a picker for each file field (both in `input_schema` and in
  `next_actions[].fields`).
- **Value shape is always list:** file field values MUST be `FileRef[]` (array). There is no scalar `FileRef` shape.
- **Per-field source selection:** per field, users MUST choose either upload OR vault/session refs. Mixing sources
  within the same field is FORBIDDEN.
- **Save to vault UX:** saving run artifacts to the vault MUST be an explicit per-artifact action (“Spara i valv”) in
  ToolRunArtifacts (and sandbox).
- **Vault management UI is REQUIRED:** the vault panel MUST support:
  - active list + soft-deleted “papperskorg” view
  - delete + restore
  - search by filename
  - sorting: Newest, Name (A–Ö), Size
  - a quota/usage bar (e.g. `x MB / y MB`) plus actionable limits messaging

## Non-goals

- Backend storage changes (PR-0054).
- Additional contract versions beyond existing file-ref field kinds.

## Implementation plan

- Picker UI: list vault files, show metadata (name/size/date) without filesystem paths.
- Default handling: preselect vault refs; show actionable error if default missing.
- Actions: save run artifacts to vault; delete/restore entries (soft delete).
- Constraints: enforce file constraints (min/max) with clear errors.
- Tests: frontend unit tests + Playwright flow (no overlap with sandbox file-refs reuse script).
- Docs: update story/epic status when done.

## Test plan

- Frontend: `pdm run fe-test`
- Playwright: vault picker flow + defaults + save/delete/restore

## Code review (as of 2026-01-28)

### ✅ Strong points

- **Vault UI scope matches the “management UI is REQUIRED” spec:** active + trash, delete/restore, sort + quota bar.
- **UX polish:** search is integrated with the input chrome (no clunky standalone “Sök” button), sort toggle stays
  single-row, and per-file actions are in a kebab menu (less repetitive “Ta bort” buttons).
- **Multi-select support:** visible checkboxes + “Markera alla/Avmarkera” + bulk delete/restore actions.
- **Download UX:** download is triggered via blob download to avoid rendering raw JSON error payloads in the browser.
- **Picker integration:** file field selection now supports picking vault refs via a modal without leaking filesystem
  paths to the client.

### ⚠️ Issues / risks

- **Orphaned bytes after deploy:** previously non-persistent `VAULT_ROOT` can cause DB rows to outlive on-disk bytes.
  UX now marks these as “Saknas på servern” and disables download/selection; consider cleanup policy once prod volume
  is deployed.
- **SRP/duplication:** `ToolFileFieldPicker.vue` and `UiActionFieldFileRef.vue` both implement similar “vault picker +
  session picker” logic. Consider extracting shared helpers/composables to avoid drift.

### 🧪 Test coverage notes

- Add focused unit tests for the vault panel (search debounce, selection limits, bulk actions).
- Update Playwright E2E to match the final DOM/ARIA contract for the picker and action menu.

## Rollback plan

- Revert commit; hide vault picker UI; keep backend intact.

## Closeout Status (as of 2026-06-18)

`PR-0359` repairs this slice to `done`. The current SPA ships the vault picker,
defaults handling, explicit save/delete/restore flows, and the governed vault
management UI described here.
