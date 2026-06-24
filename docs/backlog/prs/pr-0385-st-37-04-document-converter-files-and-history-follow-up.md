---
type: pr
id: PR-0385
title: "ST-37-04 Document Converter files and history follow-up"
status: blocked
owners: "agents"
created: 2026-06-23
updated: 2026-06-24
stories:
  - "ST-37-04"
tags:
  - document-converter
  - mina-filer
  - history
dependencies:
  - "PR-0382"
  - "PR-0384"
acceptance_criteria:
  - "Given teachers will later reuse saved files, when this follow-up is activated, then Document Converter can select supported sources from `Mina filer` as well as local upload."
  - "Given source selection is not first in the product sequence, when upload and preview are implemented, then their plumbing keeps `Mina filer` source selection easy to add without rewriting the workflow."
  - "Given first launch may use current-session history only, when durable history is planned, then the task separates visible teacher history from internal result-artifact observability."
  - "Given batch conversion creates multiple outputs, when files/history behavior is extended, then save naming, source references, and replay/reopen behavior are reviewed before implementation."
---

# PR-0385: ST-37-04 Document Converter Files And History Follow-up

## Problem

Local upload and preview should be proven first. The product should still be
plumbed so teacher-owned source selection and re-entry from saved files can be
added immediately after the upload/preview path is stable.

## Goal

Plan and implement the first `Mina filer` source selector and history
hardening follow-up after the route-visible MVP proves the core workflow.

## Blocked Until

- `PR-0384` ships or is explicitly superseded by a different route-visible MVP.
- Upload and preview behavior are proven enough that `Mina filer` can reuse the
  same source model instead of creating a parallel workflow.

## Non-goals

- No changes to the first backend/local-heavy contract unless route-visible
  evidence proves a gap.
- No public file source selection.
- No artifact-observability language in user-facing UI.

## Questions To Close

- Which saved file types can be selected at first?
- Should history be current-session only, durable per user, or attached to
  saved output files?
- How should batch outputs be named and re-opened?
- Should re-render from saved HTML/CSS projects require preserving all linked
  assets?

## Test Plan

- Red-first tests for the selected files/history contract.
- Focused backend/frontend tests for owner-scoped file selection and no
  cross-owner access.
- `pdm run lint`
- `pdm run typecheck`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Rollback Plan

Remove the files/history extensions and keep the route-visible MVP on local
upload plus current-session state.
