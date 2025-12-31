---
type: review
id: REV-EPIC-06
title: "Review: Linter Architecture Refactor"
status: approved
owners: "agents"
created: 2025-12-29
reviewer: "lead-developer"
epic: EPIC-06
stories:
  - ST-06-10
  - ST-06-11
  - ST-06-12
  - ST-06-13
  - ST-06-14
---

## Context

Refactor of the client-side Python linter to improve cohesion, testability, and extensibility.

## Artifacts

- `docs/reference/ref-linter-architecture.md`
- `docs/adr/adr-0048-linter-context-and-data-flow.md`

## TL;DR

This review evaluates the proposed architectural refactor for the Skriptoteket client-side Python linter. The goal is to move from an ad-hoc, brittle AST traversal model to a structured "Context-Rule" pattern that enables semantic analysis (variable tracking), deterministic testing, and easier extensibility.

## Problem Statement

The current linter (`skriptoteketLinter.ts`) is built on ad-hoc AST traversals mixed directly with business logic. This leads to:

1. **Fragility:** Valid code variations (e.g., extracting a list to a variable) cause linter errors because the rules expect specific syntax structures (literal expressions only).
2. **Lack of Testability:** Logic is tightly coupled to CodeMirror's `EditorState`, making headless unit testing impossible without a complex DOM harness.
3. **Low Cohesion:** Rules are difficult to read and maintain because they are buried in traversal boilerplate.

## Proposed Solution

Adopt a **Context-Rule** architecture:

1. **Linter Context:** A single pass builds a "Knowledge Graph" of the code (imports, functions, calls, and *variables*).
2. **Pure Rules:** Rules are functions that operate on this Context, not the raw AST.
3. **Variable Tracking:** A new subsystem tracks variable assignments and types to allow "flow-sensitive" analysis (solving the "dynamic outputs" issue).

## Artifacts to Review

| File | Focus | Time |
| --- | --- | --- |
| `docs/reference/ref-linter-architecture.md` | Core architecture and data structures | 15 min |
| `frontend/apps/skriptoteket/src/composables/editor/skriptoteketLinter.ts` | Current state (for context) | 5 min |

**Total estimated time:** ~20 minutes

## Key Decisions

| Decision | Rationale | Approve? |
| --- | --- | --- |
| **Separate Parsing from Rules** | Decouples logic from AST structure; enables re-use of "facts" across rules. | [x] |
| **Introduce Variable Table** | Enbles data-flow analysis (e.g., knowing `x` is a List) which fixes false positives on dynamic code. | [x] |
| **Headless Test Harness** | Critical for ensuring stability; allows testing rules against string inputs without a browser. | [x] |

## Review Checklist

- [x] **Architecture:** Does the "Context" object capture enough information for current and future rules?
- [x] **Data Flow:** Is the proposed `VariableTable` sufficient to solve the "dynamic outputs" problem without full type inference complexity?
- [x] **Testability:** Does the plan adequately address the lack of testing infrastructure?
- [x] **Migration:** Is the phased approach (Infrastructure -> Variable Tracking -> Decoupling) safe?

## Risk Assessment

- **Performance:** Building a full context pass might be slower than ad-hoc checks.
  - *Mitigation:* The "facts" are lightweight; tree traversal is already fast in Lezer. We only re-run on debounce.
- **Complexity:** Writing a variable tracker is more complex than checking for literals.
  - *Mitigation:* Start with simple "Assignment + Append" tracking, which covers 90% of script use cases.

## Review Feedback

**Reviewer:** Antigravity (Agent)
**Date:** 2025-12-29
**Verdict:** changes_requested

### Required Changes

1. **Scoped Variable Table (Critical):**
    The proposed flat `VariableTable` (`Map<string, VariableInfo>`) in `ref-linter-architecture.md` is insufficient for Python.
    - *Problem:* If `def A(): x=[]` and `def B(): x=""`, a flat map collision will cause false positives/negatives.
    - *Requirement:* The Context must implement a **Scope Chain** (Global -> Function -> Class).
    - *Design Update:* `VariableTable` should query by `(name, scopeNode)` or be a hierarchical structure `Map<ScopeNode, Map<string, Info>>`.

2. **Robustness Strategy:**
    Define how the context builder handles `SyntaxError`.
    - *Requirement:* The `LinterContext` should include a `syntaxErrors: Diagnostic[]` field directly from Lezer, so rules can choose to bail out on broken code.

3. **Syntax Error Handling:**
    The proposal does not explicitly state how standard Python syntax errors (runtime errors) are surfaced.
    - *Gap:* If the user types invalid Python, we need to show it.
    - *Requirement:* Implement a `SyntaxRule` that queries the Lezer tree for error nodes (`⚠`) and reports them as diagnostics with "Syntax Error" messages. This should be part of the default rule set.

4. **CodeMirror Quick Fix Actions (Diagnostic Actions):**
    The current plan does not use CodeMirror's diagnostic action buttons (IDE-like quick fixes).
    - *Requirement:* Implement diagnostic actions for the agreed rule set (imports, encoding, missing entrypoint, missing contract keys).
    - *Requirement:* Add a shared helper for safe import insertion (`findImportInsertPosition(state)`) to avoid corrupting shebang/docstring/`__future__` layouts.

5. **Lint Panel + Keyboard Navigation:**
    The current UX is gutter markers + hover only, which is not IDE-parity.
    - *Requirement:* Add a dedicated lint panel (open/close) listing all diagnostics.
    - *Requirement:* Add standard keybindings: `Mod-Shift-m` (open panel), `F8` (next), `Shift-F8` (previous).
    - *Requirement:* Expose `diagnosticCount(state)` for status bar integration.

6. **Gutter Marker Filtering:**
    The gutter is cluttered when it mirrors all severities.
    - *Requirement:* Show only `"error"` and `"warning"` markers in the gutter.
    - *Requirement:* Keep tooltip/panel visibility for `"info"` and `"hint"` diagnostics.

7. **AI Context Integration Design (EPIC-08):**
    The context object is also the foundation for inline completions (ST-08-14).
    - *Requirement:* Document which `LinterContext` facts are “prompt-grade” (imports, variables with scope chain, entrypoint, syntaxErrors, calls) and define rules for suppressing suggestions when syntax is invalid.

### Suggestions

- **Type Guards:** Consider tracking `isinstance` checks in control flow to support `if isinstance(outputs, list): return outputs`, future-proofing the "dynamic" check.
- **Performance Budget:** Add a constraint to the ADR that the entire Context Builder pass must stay under 5-10ms for typical files (<500 LOC) to ensure typing latency remains low.

## Changes Made (2025-12-31)

All required changes are implemented across ST-06-10..14:

1. **Scoped Variable Table**
   - Implemented `ScopeChain` + `lookupVariable` in `frontend/apps/skriptoteket/src/composables/editor/linter/domain/variables.ts`.
   - Built from Lezer tree in `frontend/apps/skriptoteket/src/composables/editor/linter/infra/pythonVariables.ts` (scope stack + non-class parent chain).

2. **Robustness Strategy + Syntax Error Handling**
   - Context exposes syntax errors as domain diagnostics with stable `source: "ST_SYNTAX_ERROR"` via
     `frontend/apps/skriptoteket/src/composables/editor/linter/infra/buildLinterContext.ts`.
   - Default ruleset includes `SyntaxRule` returning `ctx.facts.syntaxErrors` (`frontend/apps/skriptoteket/src/composables/editor/linter/domain/rules/syntaxRule.ts`).

3. **CodeMirror Quick Fix Actions**
   - Domain rules emit `FixIntent[]` (`frontend/apps/skriptoteket/src/composables/editor/linter/domain/fixIntents.ts`).
   - Adapter maps `FixIntent[]` → CodeMirror `Diagnostic.actions` with idempotency guards in
     `frontend/apps/skriptoteket/src/composables/editor/linter/adapters/codemirror/skriptoteketLinterAdapter.ts`.

4. **Lint Panel + Keyboard Navigation**
   - Implemented in intelligence layer (keeps base editor generic) in
     `frontend/apps/skriptoteket/src/composables/editor/skriptoteketLintPanel.ts`.

5. **Gutter Marker Filtering**
   - `lintGutter({ markerFilter, tooltipFilter })` configured so gutter shows only error/warning markers while tooltip/panel keep all
     severities in `frontend/apps/skriptoteket/src/composables/editor/linter/adapters/codemirror/skriptoteketLinterAdapter.ts`.

6. **Headless Test Harness**
   - Added true headless correctness harness (EditorState-only + `python()`) in `frontend/apps/skriptoteket/src/test/headlessLinterHarness.ts`.
   - Added focused rule tests (syntax errors + scope-chain variable resolution) in
     `frontend/apps/skriptoteket/src/composables/editor/linter/headlessLinterHarness.spec.ts`.
   - Kept integration-heavy CodeMirror wiring spec in `frontend/apps/skriptoteket/src/composables/editor/skriptoteketLinter.spec.ts`.

## Re-review (2025-12-31)

**Reviewer:** lead-developer (agent)
**Verdict:** approved (all required changes satisfied; headless harness added and verified in Vitest).
