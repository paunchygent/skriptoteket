---
type: story
id: ST-14-24
title: "UI contract: first-class file references (picker + action fields)"
status: ready
owners: "agents"
created: 2025-12-29
updated: 2026-01-20
epic: "EPIC-14"
acceptance_criteria:
  - "Given a run has uploaded input files, when a tool emits next_actions that accept file references, then the UI can present selectable file options without exposing runner filesystem paths."
  - "Given a user submits an action containing file references, when the runner executes the tool, then the referenced files resolve to the correct on-disk paths within the run/session sandbox."
  - "Given a file reference is invalid or not available in the current run/session, when normalizing or executing, then the platform returns an actionable validation error (no 500)."
  - "Given a tool does not use file references, when running multi-step tools, then behavior remains unchanged."
dependencies:
  - "ST-19-02"
  - "ST-19-01"
  - "ST-19-03"
  - "ST-14-19"
ui_impact: "Yes (inputs/actions UI + runner integration)"
data_impact: "No (references travel in existing payload/state; no DB migration required)"
---

## Context

Today, tools must know (or assume) that uploaded files land under `/work/input/...` and must manually pass file names via
state to later steps. This works, but it’s leaky and brittle.

## Goal

Add a first-class, stable “file reference” concept to the UI contract so tools can ask users to select files from the
current run/session without hard-coding paths.

## Notes

File references are identifiers (not paths). The UI must only present names/labels and never leak internal filesystem
paths; this keeps the contract compatible with future file sources (e.g. per-user reusable file libraries) without
breaking UX.

Reference: `docs/reference/ref-tool-editor-dx-review-2025-12-29.md`

### Dependency alignment (no parallel mechanisms)

- The backend-side file reference model and resolver is implemented in ST-19-02.
- UI work in this story should be limited to:
  - adding a file-ref field kind to action schemas,
  - rendering a picker populated by the platform’s “available file refs” API,
  - submitting selected file refs as action input values.
- Do not introduce a UI-only “file id” or path-based fallback; the only identity is `FileRef` values and the only
  staging pipeline is the platform resolver.
