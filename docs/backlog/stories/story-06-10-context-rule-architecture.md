---
type: story
id: ST-06-10
title: "Context-Rule linter architecture foundation"
status: ready
owners: "agents"
created: 2025-12-29
epic: "EPIC-06"
acceptance_criteria:
  - "Given the linter runs, when diagnostics are computed, then a single LinterContext is built once per lint pass and shared across rules"
  - "Given Python code contains syntax errors, when diagnostics are computed, then ctx.facts.syntaxErrors contains parse diagnostics and a default SyntaxRule surfaces them to the user"
  - "Given code contains multiple lexical scopes, when variables are tracked, then variable lookup is scope-aware (ScopeChain) and does not collide across sibling scopes"
  - "Given ctx.facts.syntaxErrors is non-empty, when non-syntax rules run, then they bail out to avoid cascading false positives"
ui_impact: "Improves editor lint stability and reduces false positives; adds visible syntax error reporting."
dependencies: ["REV-EPIC-06", "ADR-0048"]
---

## Context

The current linter mixes AST traversal with rule logic and lacks a robust foundation for:

- headless tests (rules are tightly coupled to `EditorState`)
- scope-aware variable tracking (Python lexical scopes)
- predictable behavior on invalid/incomplete Python while typing

This story introduces a shared `LinterContext` and a default `SyntaxRule`, forming the foundation for quick fixes,
lint panel navigation, and AI completion context.

## Scope

- Create a `buildLinterContext(state)` factory that collects:
  - `syntaxErrors` (Lezer error nodes → `Diagnostic[]`)
  - imports, symbols (functions/classes), calls/returns
  - `variables` as a scope-aware `ScopeChain`
- Refactor the linter to:
  - build context once
  - run a set of pure rules on that context
  - include a default `SyntaxRule`

## Files

### Create

- `frontend/apps/skriptoteket/src/composables/editor/skriptoteketLinterContext.ts`
- `frontend/apps/skriptoteket/src/composables/editor/rules/syntaxRule.ts`

### Modify

- `frontend/apps/skriptoteket/src/composables/editor/skriptoteketLinter.ts`
- `frontend/apps/skriptoteket/src/composables/editor/skriptoteketPythonAnalysis.ts`
- `frontend/apps/skriptoteket/src/composables/editor/skriptoteketPythonTree.ts`
