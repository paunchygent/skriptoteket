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
- **Variable Table (New):** A lightweight track of variable assignments and operations, scoped by Python lexical scope.
- **Syntax Errors (New):** Standardized diagnostics for Lezer parse errors (broken code).

**Robustness strategy:** the context builder MUST NOT throw on invalid/incomplete Python. It always returns a
`LinterContext` and stores parse errors in `facts.syntaxErrors`, so rules can bail out or degrade behavior.

### 2. Variable Tracking (Heuristic Data Flow + Scope Chain)

We will track variable types based on **assignment** and **usage**:

- `x = [...]` -> `x` is `List` (source: assignment)
- `x.append(...)` -> `x` is `List` (source: operation)
- `x = {}` -> `x` is `Dict` (source: assignment)

This allows rules to verify `return {"outputs": x}` by checking if `x` is known to be a list, downgrading errors to warnings if the type is unknown/dynamic.

**Scope correctness (required):** the variable table MUST be scoped. A flat `Map<string, VariableInfo>` is insufficient.

- Track variables in a **Scope Chain**: `Map<ScopeNode, Map<string, VariableInfo>>`.
- Variable lookup is `lookup(name, scopeNode)` with fallback to parent scopes.
- `ScopeNode` represents Python lexical scopes (IDE-like behavior):
  - Include: module, function/async function, class body, lambda, comprehensions.
  - Exclude: `if/for/while/try/with/match` blocks (not scopes in Python).
  - Note: class scope is special in Python; method bodies do not resolve free names through the class scope. The scope
    chain MUST reflect this (methods should link to module scope, not class body scope).

### 3. Pure Rules

Rules become pure functions that operate on the `Context`, not the `EditorState`. This enables **headless unit testing** by mocking the context.

### 4. Syntax Error Surfacing (Default Rule)

Broken code MUST produce visible diagnostics for the user (similar to VS Code "Problems"):

- The context builder walks the Lezer tree for error nodes and returns `Diagnostic[]` in `facts.syntaxErrors`.
- A `SyntaxRule` includes `facts.syntaxErrors` in the default rule set so parse errors always surface.

### 5. Quick Fixes (Diagnostic Actions)

Rules MAY attach CodeMirror quick-fix actions to diagnostics using `Diagnostic.actions` (IDE-like “Quick Fix…”).

- Each action is a small, safe edit implemented via `apply(view, from, to)`.
- For import-related fixes, use a shared helper `findImportInsertPosition(state)` that inserts:
  1) after shebang + encoding cookie (PEP 263), 2) after module docstring, 3) after any `from __future__ ...` imports,
  2) into/after the top-of-file import block.

### 6. AI Context Integration (EPIC-08)

The `LinterContext` is also the structured source of truth for future inline completions (ST-08-14):

- `imports` / `variables` improve suggestion relevance (what is already available; what names mean in scope)
- `entrypoint` and `returns` help generate Contract v2 compliant code
- `syntaxErrors` can suppress suggestions while code is invalid

## Consequences

### Positive

- **Reduced False Positives:** Valid dynamic code patterns will no longer trigger errors.
- **Testability:** Rules can be unit-tested with string inputs, ensuring regression safety.
- **Extensibility:** New rules (e.g., security checks) can query the Context ("is `subprocess` imported?") without re-parsing the tree.
- **IDE-like UX:** Quick fixes, keyboard navigation, and a lint panel become straightforward to implement.

### Negative

- **Complexity:** The Context Builder is more complex than ad-hoc checks.
- **Performance:** Building the full context takes more time than a single regex, but Lezer is fast enough for ~1000 LOC on the main thread (debounced).

**Performance budget (required):** the full context pass (parse + fact extraction) SHOULD remain under ~10ms for typical
scripts (<500 LOC) to preserve typing latency. If exceeded, reduce work done in the context pass and/or increase
debounce.

## Implementation Strategy

1. **Phase 1:** Extract existing AST parsers into a `buildLinterContext` factory.
2. **Phase 2:** Implement `ScopeChain` variable tracking + syntax error extraction and add a default `SyntaxRule`.
3. **Phase 3:** Split rules into separate files, add quick-fix actions, and add headless unit tests.
