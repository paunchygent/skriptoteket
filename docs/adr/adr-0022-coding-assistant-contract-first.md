---
type: adr
id: ADR-0022
title: "Coding Assistant: Contract-First Validation"
status: proposed
owners: "agents"
deciders: ["user-lead"]
created: 2025-12-19
supersedes: []
links:
  - ADR-0015
  - PRD-script-hub-v0.3
---

## Context

The script editor will gain a coding assistant to help contributors write compliant scripts. We must decide:

1. **Where validation rules come from** - hardcoded, configurable, or derived?
2. **Where validation runs** - client-side, server-side, or hybrid?
3. **What the assistant scope is** - linting only, or AI-powered suggestions?

## Decision

### 1. Contract-First: Single Source of Truth

All validation rules derive from a **machine-readable contract schema**:

```
src/skriptoteket/contracts/
  script-api-v1.yaml    # Contract definition
  validation.py         # Rules derived from schema
```

**Why**: Prevents drift between documentation, validation, and runtime behavior. The contract file is authoritative.

### 2. Server-Side Validation Only

Validation runs on the server via a dedicated endpoint:

```
POST /api/v1/admin/versions/{id}/validate → ValidationResult
```

**Why**:
- Python AST analysis requires Python runtime
- Contract schema can evolve without SPA rebuild
- Simpler client (just display results)

**Trade-off**: No offline validation. Acceptable because editor requires network for save anyway.

### 3. Validation, Not Generation (v0.3)

The assistant **validates and explains**, but does not generate or autocomplete code.

**Why**:
- AI generation is a larger scope (prompt engineering, rate limits, costs)
- Validation alone solves the immediate problem (failed runs from contract violations)
- Generation can be added in v0.4 as an additive feature

## Consequences

### Positive

- **No rule drift**: Contract schema is the single source for validation, API sidebar, and docs
- **Testable**: Validation logic is pure Python, easily unit tested
- **Extensible**: Adding v0.2 features (memory.json) means updating the schema, not scattered code
- **Lightweight client**: Vue component only displays results, no Python parsing in browser

### Negative

- **Network required**: Every validation requires server round-trip
- **No keystroke validation**: Only validates on save (acceptable for v0.3)
- **Schema maintenance**: Contract file must be kept in sync with runner changes

### Neutral

- AST-based validation catches static patterns only (path literals, imports, signatures)
- Runtime violations (actual file sizes, memory usage) still require sandbox execution

## Implementation Notes

### Contract Schema Structure

```yaml
version: 1
entrypoint:
  name: run_tool
  parameters: [{name: input_path, type: str}, {name: output_dir, type: str}]
  returns: str

blocked_imports: [requests, urllib, socket, httpx, aiohttp]

output_paths:
  allowed_prefix: "output/"
  disallowed_patterns: ["..", "/"]
```

### Validation Categories

| Category | Method | Catches |
|----------|--------|---------|
| Syntax | `compile()` | Parse errors |
| Signature | AST inspection | Wrong function name, parameters |
| Imports | AST inspection | Network modules |
| Paths | AST string literals | Traversal patterns |

### Future: AI Generation (v0.4)

When adding AI assistance:
- Contract schema provides system prompt context
- Validation runs on generated code before insertion
- Same endpoint, new `suggest: true` parameter
