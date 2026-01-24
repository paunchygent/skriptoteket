---
type: pr
id: PR-0055
title: "User file vault: UI picker + defaults"
status: ready
owners: "agents"
created: 2026-01-24
updated: 2026-01-24
stories:
  - "ST-14-36"
tags: ["frontend"]
acceptance_criteria:
  - "Vault files appear in run/action pickers and respect file constraints."
  - "Vault default refs preselect when available; missing defaults block execution with validation error."
  - "Users can save artifacts to vault and delete/restore entries from the picker."
---

## Problem

ST-14-36 needs a user-facing picker for vault files, plus default preselect behavior and validation. Without a UI,
vault refs are not actionable.

Parent: EPIC-14. Depends on PR-0054 backend endpoints and PR-0053 UI contract behavior.

## Goal

Deliver the vault picker UI for runs/actions, handle defaults, and support save/delete/restore flows with clear UX.

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

## Rollback plan

- Revert commit; hide vault picker UI; keep backend intact.
