---
type: prd
id: PRD-script-hub-v0.3
title: "Script Hub PRD v0.3: Coding Assistant"
status: draft
owners: "agents"
created: 2025-12-19
product: "script-hub"
version: "0.3"
depends_on:
  - PRD-script-hub-v0.2
  - Vue/Vite SPA migration (editor pages)
---

## Summary

Add a **coding assistant** to the script editor that helps contributors write scripts compliant with site restrictions. The assistant validates scripts against the execution contract and provides contextual guidance.

## Philosophy: Inside-Out

The assistant is built from the **execution contract outward**:

```
┌─────────────────────────────────────────────────────────┐
│                    EXECUTION CONTRACT                   │
│  (result.json schema, path safety, resource limits)     │
├─────────────────────────────────────────────────────────┤
│                    VALIDATION RULES                     │
│  (derived directly from contract, machine-readable)     │
├─────────────────────────────────────────────────────────┤
│                    ASSISTANT UI                         │
│  (displays validation results, offers guidance)         │
└─────────────────────────────────────────────────────────┘
```

**Principle**: Every assistant feature must trace back to a documented contract or constraint. No invented rules.

## Goals

1. **Reduce failed sandbox runs** by catching common errors before execution
2. **Teach the API** through contextual hints, not documentation links
3. **Stay invisible when not needed** - no intrusive overlays or modals

## Non-Goals

- AI-generated code suggestions (v0.4+)
- Real-time collaboration features
- Offline validation (requires SPA, so network available)
- Custom linting rules per tool

## Core Concept: Contract-Derived Validation

All validation rules derive from existing, documented constraints:

| Source Document | Validation Rule |
|-----------------|-----------------|
| ADR-0015 (runner contract) | `result.json` schema check |
| ADR-0015 (path safety) | Artifact paths under `output/` only |
| `docker_runner.py` | Function signature `run_tool(input_path, output_dir) -> str` |
| `docker_runner.py` | No network imports (`requests`, `urllib`, `socket`) |
| `config.py` | Output size awareness (html_output < 500KB) |
| PRD v0.2 | `memory.json` and `ui_schema.json` patterns |

## Requirements

### R1: Validation on Save

When the user saves a draft, validate the script and display results inline.

**Validates**:
- Python syntax (compile check)
- Entrypoint function exists and has correct signature
- No blocked imports (network modules)
- Path literals use relative paths under `output/`

**Does not validate** (requires execution):
- Runtime behavior
- Actual output sizes
- Memory/CPU usage

### R2: Inline Error Display

Errors and warnings appear **in the editor gutter**, not in a separate panel.

- Syntax errors: red squiggle + line number
- Contract violations: yellow warning + explanation
- Click to see full message

### R3: API Reference Sidebar

A collapsible sidebar showing the current API contract:

```
┌─────────────────────────────────┐
│ Skriptoteket API v1             │
├─────────────────────────────────┤
│ def run_tool(                   │
│   input_path: str,              │
│   output_dir: str               │
│ ) -> str  # HTML                │
├─────────────────────────────────┤
│ Environment:                    │
│ • SKRIPTOTEKET_INPUT_PATH       │
│ • SKRIPTOTEKET_OUTPUT_DIR       │
│ • SKRIPTOTEKET_MEMORY_PATH (v2) │
├─────────────────────────────────┤
│ Constraints:                    │
│ • No network access             │
│ • Write to output/ only         │
│ • Return HTML string            │
└─────────────────────────────────┘
```

### R4: Contract Schema File

Create a machine-readable contract file that drives both validation and UI:

```yaml
# src/skriptoteket/contracts/script-api-v1.yaml
version: 1
entrypoint:
  name: run_tool
  parameters:
    - name: input_path
      type: str
    - name: output_dir
      type: str
  returns: str

environment:
  - SKRIPTOTEKET_INPUT_PATH
  - SKRIPTOTEKET_OUTPUT_DIR
  - SKRIPTOTEKET_RESULT_PATH

blocked_imports:
  - requests
  - urllib
  - urllib3
  - httpx
  - socket
  - aiohttp

output_paths:
  allowed_prefix: "output/"
  disallowed_patterns:
    - ".."
    - "/"  # absolute paths
```

**Principle**: One source of truth. Validation rules, API sidebar, and documentation all derive from this file.

## User Stories

### US1: Contributor catches signature error before running

> As a contributor, I save a script with `def main(file):` and immediately see a warning: "Expected function `run_tool(input_path, output_dir)`, found `main(file)`". I rename the function and the warning disappears.

### US2: Contributor learns about path safety

> As a contributor, I write `open("/work/output/../secrets.txt")` and see a warning on that line: "Path traversal detected. Artifacts must be under `output/` with no `..` segments." I fix the path to `output/report.txt`.

### US3: Contributor references the API

> As a contributor writing my first script, I open the API sidebar and see the exact function signature and available environment variables. I copy the signature and start coding.

## Architecture

### Validation Flow

```
User saves draft
       │
       ▼
POST /api/v1/admin/versions/{id}/save
       │
       ├──► Save to database
       │
       ▼
POST /api/v1/admin/versions/{id}/validate (async, non-blocking)
       │
       ▼
Python AST analysis (server-side)
       │
       ▼
Return validation result (JSON)
       │
       ▼
Vue component displays inline markers
```

### Validation Endpoint

```python
# New endpoint
POST /api/v1/admin/versions/{version_id}/validate

# Response
{
  "valid": false,
  "errors": [
    {"line": 1, "column": 4, "code": "E001", "message": "..."}
  ],
  "warnings": [
    {"line": 15, "column": 8, "code": "W002", "message": "..."}
  ]
}
```

### Error Codes

| Code | Category | Example |
|------|----------|---------|
| E001 | Syntax | Invalid Python syntax |
| E002 | Signature | Missing `run_tool` function |
| E003 | Signature | Wrong parameter names/count |
| W001 | Import | Blocked module imported |
| W002 | Path | Path traversal pattern detected |
| W003 | Path | Absolute path literal detected |

## Implementation Scope

### In Scope (v0.3)

- Contract schema YAML file
- Validation endpoint (AST-based)
- Vue component: inline error markers
- Vue component: API reference sidebar
- Error code catalog

### Out of Scope (v0.4+)

- AI-powered suggestions ("fix this for me")
- Autocomplete for `memory.json` keys
- `ui_schema.json` visual preview
- Real-time validation (on keystroke)

## Success Metrics

| Metric | Target |
|--------|--------|
| Failed sandbox runs due to signature errors | < 5% (down from ~20%) |
| Contributors who open API sidebar | > 50% on first script |
| Time from "new draft" to "first successful run" | < 10 minutes |

## Dependencies

- **Vue/Vite SPA migration** of editor pages (prerequisite)
- **PRD v0.2 features** inform contract schema (memory, multi-file)

## Effort Estimate

| Component | Hours |
|-----------|-------|
| Contract schema + validation logic | 8 |
| Validation endpoint | 4 |
| Vue inline error display | 6 |
| Vue API sidebar | 4 |
| Tests + documentation | 6 |
| **Total** | **28** |

## Open Questions

1. **Validation trigger**: On save only, or also on "Testkör" button?
   - Recommendation: On save (simpler, covers the common case)

2. **Contract versioning**: How to handle v0.2 features (memory.json)?
   - Recommendation: Contract schema has `version` field; validation adapts

3. **Blocked imports granularity**: Block entire `urllib` or just `urllib.request`?
   - Recommendation: Block at package level (simpler, safer)
