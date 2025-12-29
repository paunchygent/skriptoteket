---
type: review
id: REV-EPIC-06
title: "Review: Linter Architecture Refactor"
status: changes_requested
owners: "agents"
created: 2025-12-29
reviewer: "lead-developer"
epic: EPIC-06
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
- [ ] **Testability:** Does the plan adequately address the lack of testing infrastructure?
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

### Suggestions

- **Type Guards:** Consider tracking `isinstance` checks in control flow to support `if isinstance(outputs, list): return outputs`, future-proofing the "dynamic" check.
- **Performance Budget:** Add a constraint to the ADR that the entire Context Builder pass must stay under 5-10ms for typical files (<500 LOC) to ensure typing latency remains low.
