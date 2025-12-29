---
type: story
id: ST-06-14
title: "Headless linter rule test harness"
status: ready
owners: "agents"
created: 2025-12-29
epic: "EPIC-06"
acceptance_criteria:
  - "Given a rule and a code string, when tests run, then the rule can be evaluated headlessly without a browser DOM"
  - "Given a test asserts diagnostics, when assertions run, then they can reference rule source IDs and stable ranges/messages"
  - "Given syntax errors in code, when the syntax rule runs, then tests cover Lezer error nodes mapping to diagnostics"
ui_impact: "None (dev-only); improves regression safety for editor linting."
dependencies: ["ST-06-10"]
---

## Context

The linter must be testable as a pure function of code input. Headless testing prevents regressions when rules evolve
and makes the architecture refactor safe.

## Scope

- Add a Vitest harness to build a minimal test context from a code string.
- Add focused unit tests for:
  - syntax rule behavior
  - scope chain variable resolution (representative cases)

## Files

### Create

- `frontend/apps/skriptoteket/src/composables/editor/skriptoteketLinter.spec.ts`
