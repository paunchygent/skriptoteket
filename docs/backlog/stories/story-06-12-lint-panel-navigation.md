---
type: story
id: ST-06-12
title: "Lint panel and keyboard navigation"
status: ready
owners: "agents"
created: 2025-12-29
epic: "EPIC-06"
acceptance_criteria:
  - "Given diagnostics exist, when the user presses Mod-Shift-m, then the lint panel opens and lists all diagnostics"
  - "Given diagnostics exist, when the user presses F8, then the selection jumps to the next diagnostic"
  - "Given diagnostics exist, when the user presses Shift-F8, then the selection jumps to the previous diagnostic"
  - "Given the UI needs a status summary, when diagnosticCount(state) is queried, then the count reflects current diagnostics"
ui_impact: "Adds a dedicated Problems/Lint panel (VS Code parity) and standard keyboard navigation."
dependencies: ["ST-06-10", "docs/reference/ref-codemirror-integration.md"]
---

## Context

Hover-only diagnostics do not scale. IDEs provide:

- a Problems panel listing all issues
- keyboard navigation between issues

CodeMirror supports this via `openLintPanel`, `closeLintPanel`, and `nextDiagnostic`/`previousDiagnostic`.

## Scope

- Add a small integration module that:
  - exposes commands to open/close the lint panel
  - installs `lintKeymap` plus `Shift-F8` binding for previous diagnostic
  - optionally exposes `diagnosticCount(state)` for UI status integration

## Files

### Create

- `frontend/apps/skriptoteket/src/composables/editor/skriptoteketLintPanel.ts`
