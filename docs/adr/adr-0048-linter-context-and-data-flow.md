---
type: adr
id: ADR-0048
title: "Linter context and data flow (Context-Rule-Visitor)"
status: proposed
owners: "agents"
deciders: ["agents", "lead-developer"]
created: 2025-12-29
supersedes: []
---

## Context

The current client-side linter for Skriptoteket (ADR-0035) relies on ad-hoc syntax tree traversals mixed with validation logic. While this works for simple static checks, it fails on common code patterns:

1. **Dynamic Construction:** Valid return dictionaries built progressively (`outputs.append(...)`) are flagged as errors because the linter expects literal list expressions.
2. **Coupling:** Rules are tightly bound to the AST structure, making them brittle and hard to test.
3. **No Data Flow:** The linter has no concept of variables, so it cannot "see" that a variable `x` holds a list.

We need a robust way to analyze "dynamic but deterministic" code without implementing a full Python interpreter or type checker.

## Decision

We will refactor the linter to use a **Context-Rule** architecture with lightweight data-flow tracking.

### 1. The Linter Context (Single Source of Truth)

Instead of rules traversing the tree, we run a single **Context Pass** that builds a "Knowledge Graph" of the code:

- **Import Graph:** What is imported and aliased?
- **Symbol Table:** Where are functions and classes defined?
- **Control Flow:** Where are calls and return statements?
- **Variable Table (New):** A lightweight track of variable assignments and operations.

### 2. Variable Tracking (Heuristic Data Flow)

We will track variable types based on **assignment** and **usage**:

- `x = [...]` -> `x` is `List` (source: assignment)
- `x.append(...)` -> `x` is `List` (source: operation)
- `x = {}` -> `x` is `Dict` (source: assignment)

This allows rules to verify `return {"outputs": x}` by checking if `x` is known to be a list, downgrading errors to warnings if the type is unknown/dynamic.

### 3. Pure Rules

Rules become pure functions that operate on the `Context`, not the `EditorState`. This enables **headless unit testing** by mocking the context.

## Consequences

### Positive

- **Reduced False Positives:** Valid dynamic code patterns will no longer trigger errors.
- **Testability:** Rules can be unit-tested with string inputs, ensuring regression safety.
- **Extensibility:** New rules (e.g., security checks) can query the Context ("is `subprocess` imported?") without re-parsing the tree.

### Negative

- **Complexity:** The Context Builder is more complex than ad-hoc checks.
- **Performance:** Building the full context takes more time than a single regex, but Lezer is fast enough for ~1000 LOC on the main thread (debounced).

## Implementation Strategy

1. **Phase 1:** Extract existing AST parsers into a `buildLinterContext` factory.
2. **Phase 2:** Implement `VariableTable` and update `contractDiagnostics` to use it.
3. **Phase 3:** Split rules into separate files and add unit tests.
