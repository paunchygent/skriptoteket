---
type: story
id: ST-14-24
title: "UI contract v2.x: first-class file references"
status: ready
owners: "agents"
created: 2025-12-29
updated: 2026-01-03
epic: "EPIC-14"
acceptance_criteria:
  - "Given a run has uploaded input files, when a tool emits next_actions that accept file references, then the UI can present selectable file options without exposing runner filesystem paths."
  - "Given a user submits an action containing file references, when the runner executes the tool, then the referenced files resolve to the correct on-disk paths within the run/session sandbox."
  - "Given a file reference is invalid or not available in the current run/session, when normalizing or executing, then the platform returns an actionable validation error (no 500)."
  - "Given a tool does not use file references, when running multi-step tools, then behavior remains unchanged."
dependencies:
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
