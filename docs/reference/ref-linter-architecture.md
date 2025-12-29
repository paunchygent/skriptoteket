---
type: reference
id: REF-linter-architecture
title: "Skriptoteket Linter Architecture"
status: active
owners: "agents"
created: 2025-12-29
topic: "Target architecture for the client-side Python linter (Context-Rule pattern)"
---

## Overview

**Context:** [Review: Linter Architecture Refactor](../backlog/reviews/review-epic-06-linter-architecture-refactor.md) | [ADR-0048](../adr/adr-0048-linter-context-and-data-flow.md)

This document defines the target architecture for the Skriptoteket Python Linter (client-side in the browser). The goal is to move from ad-hoc AST traversal to a structured, testable, and deterministic "Context-Rule-Visitor" pattern.

## Problem Statement

The current linter implementation (`skriptoteketLinter.ts`) suffers from:

1. **Low Cohesion:** Rules are tightly coupled with low-level AST traversal logic.
2. **Fragility:** Rules fail on valid code variations (e.g., extracting a dict to a variable) because they rely on specific syntax structures rather than semantic facts.
3. **Lack of Testability:** Logic depends heavily on `EditorState` (CodeMirror), making headless unit testing difficult.
4. **No Extensibility:** Adding new rules requires duplicating traversal boilerplate.

## Target Architecture

We will adopt a **Context-Rule** pattern where a shared context aggregates semantic "facts" about the code, and rules are pure functions that operate on these facts.

### 1. The Linter Context (Single Source of Truth)

Instead of every rule re-parsing the syntax tree, we build a rich context object once per lint pass. This context acts as the "Knowledge Graph" for the current script.

```typescript
interface LinterContext {
  // Raw access (use sparingly)
  state: EditorState;
  tree: Tree;

  // Semantic Facts (Pre-computed)
  facts: {
    // Import graph
    imports: ImportBindings;

    // Symbol definitions
    functions: FunctionDefinition[];
    classes: ClassDefinition[];

    // Critical landmarks
    entrypoint: FunctionDefinition | null; // e.g., run_tool

    // Control flow / Usage
    calls: CallExpression[];
    returns: ReturnStatement[];

    // Data Flow (The missing piece)
    variables: VariableTable;
  };
}
```

### 2. Variable Tracking (Data Flow)

To solve issues with dynamic code construction (like the `outputs` list), we implement a lightweight `VariableTable`.

```typescript
interface VariableInfo {
  name: string;
  type: "List" | "Dict" | "String" | "Unknown";
  assignedAt: number; // position
  operations: string[]; // e.g., ["append", "extend"]
}

type VariableTable = Map<string, VariableInfo>;
```

**Behavior:**

- **Assignment:** `x = []` → Record `x` as `List`.
- **Modification:** `x.append(...)` → Record `append` operation on `x`.
- **Usage:** `return {"outputs": x}` → Look up `x` in table to verify it's a list.

### 3. The Rule Interface

Rules are decoupled from AST traversal. They accept the context and return standard diagnostics.

```typescript
interface LintRule {
  id: string; // e.g., "ST001"
  severity: "error" | "warning" | "info" | "hint";
  check(context: LinterContext): Diagnostic[];
}
```

**Example Rule (Contract Validation):**

```typescript
const ContractRule: LintRule = {
  id: "ST002",
  severity: "error",
  check(ctx) {
    if (!ctx.facts.entrypoint) return [];

    // Logic uses facts, not cursor traversal
    const returns = ctx.facts.returns.filter(r =>
      isInside(r, ctx.facts.entrypoint)
    );

    return returns.flatMap(ret => validateReturn(ret, ctx.facts.variables));
  }
};
```

## Implementation Strategy

### Phase 1: Infrastructure & Harness

1. **Extract parsers:** Move AST traversal logic from `skriptoteketLinter.ts` to dedicated parsers in `skriptoteketPythonAnalysis.ts`.
2. **Context Factory:** Create `buildLinterContext(state)` function.
3. **Test Harness:** Create a `runRule(rule, codeString)` helper that mocks `EditorState` for unit tests.

### Phase 2: Variable Tracking

1. **Implement `VariableTable` population logic.**
2. **Update `contractDiagnostics` to use `ctx.facts.variables` for type inference.**
3. **Downgrade "dynamic construction" errors to warnings if type inference is inconclusive.**

### Phase 3: Decoupling

1. **Split rules into individual files (e.g., `rules/security.ts`, `rules/best-practices.ts`).**
2. **Refactor `skriptoteketLinter` to simply orchestrate `buildLinterContext` -> `rules.map(r => r.check(ctx))`.**

## Verification Plan

### Unit Tests (New)

The new architecture allows deterministic testing:

- **Input:** String of Python code.
- **Action:** Run specific Rule.
- **Assert:** Expected diagnostics (line number, message).

### Smoke Tests

- Run `pdm run ui-editor-smoke` to ensure CodeMirror integration remains stable.
- Manual check of "broken" scripts that previously triggered false positives.
