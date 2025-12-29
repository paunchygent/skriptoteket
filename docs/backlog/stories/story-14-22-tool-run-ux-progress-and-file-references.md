---
type: story
id: ST-14-22
title: "Tool run UX: conventions for progress + input file references"
status: ready
owners: "agents"
created: 2025-12-29
epic: "EPIC-14"
acceptance_criteria:
  - "Given a tool sets progress metadata in state using a documented convention, when the UI renders the run, then it shows a compact progress indicator (e.g. step X of Y, optional label)."
  - "Given progress metadata is absent or invalid, when the UI renders the run, then it does not show a progress UI and does not error."
  - "Given a run has uploaded input files, when the UI renders actions, then it exposes a 'Files available' view (names + copyable runner paths) so authors/users can reference them in subsequent steps."
  - "Given the conventions are implemented, then they are documented for tool authors (including how to store file selections in state and how to resolve paths in the runner)."
dependencies:
  - "ST-14-19"
ui_impact: "Yes (runtime/tool-run + editor sandbox runner)"
data_impact: "No"
---

## Context

Multi-step tools need basic “flow UX” (where am I, what’s next, what files do I have) but the current UI contract focuses
on a single run response and next actions only.

We can close a large part of this gap with a small set of conventions that are rendered by the UI, without requiring a
contract breaking change.

## Goal

Support multi-step tools with a progress indicator and a clear way to reference previously uploaded files.

## Notes

Reference: `docs/reference/ref-tool-editor-dx-review-2025-12-29.md`
