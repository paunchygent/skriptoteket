---
type: reference
id: REF-SKRIPT-GENERAL-runner-contract-v3-structured-results-state-promotions
title: Runner Contract V3 - Structured Results, State & Promotions
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: active
reference_kind: general
retired_ids:
- REF-runner-contract-v3
summary: Runner Contract V3 - Structured Results, State & Promotions
---

## Overview

### Purpose And Summary

### Overview

Runner Contract V3 is the authoritative interface between the Skriptoteket platform and tool scripts running in Docker. It provides structured error handling, unambiguous state updates, and support for session promotions.

Related documents:

* ADR-0065: Runner contract v3
* ADR-0063: Runner request envelope v1
* ADR-0064: File references and resolver

### Execution Environment

* **OS:** Debian-based (Docker)
* **Python:** 3.13+
* **Network:** Disabled (`--network none`)
* **Filesystem:** Read-only except for `/work` and `/tmp`.
* **Work Directory:** `/work`
* **Entrypoint:** Default is `run_tool(input_dir: str, output_dir: str) -> dict | str`.

### Request Inputs (Environment)

The platform provides inputs via a structured JSON envelope (`/work/request.json`) and environment variables.

**Primary Mechanism (V3):**
The `skriptoteket_toolkit` library reads from `/work/request.json`. This file contains all inputs, file references, and action payloads in a unified structure.

**Legacy/Secondary (Environment Variables):**
Direct access to these is supported but discouraged in favor of the toolkit.

| Variable | Description |
| :------- | :---------- |
| `SKRIPTOTEKET_INPUTS` | JSON object containing form inputs. |
| `SKRIPTOTEKET_INPUT_DIR` | Path to input files directory (default: `/work/input`). |
| `SKRIPTOTEKET_ACTION` | JSON object for multi-step tools. |
| `SKRIPTOTEKET_MEMORY_PATH` | Path to memory JSON file (settings). |

**Recommendation:** Always use `skriptoteket_toolkit`.

### Result Contract (`result.json`)

The script must write its result to `/work/result.json` (handled automatically if using the standard `_runner.py`).

### Schema (V3)

```json
{
  "contract_version": 3,
  "status": "succeeded|failed|timed_out",
  "outputs": [...],
  "next_actions": [...],
  "state_update": {
    "kind": "no_change|clear|set",
    "state": { ... }
  },
  "error_summary": "User-safe error message",
  "error": {
    "kind": "tool_user_error|tool_runtime_error|contract_violation",
    "code": "ERROR_CODE",
    "details": { ... }
  },
  "artifacts": [...],
  "promotions": {
    "requests": [...],
    "results": [...]
  }
}
```

### State Updates

Unlike V2, V3 requires explicit state update semantics:

* `no_change`: Keep the existing session state.
* `clear`: Delete the session state.
* `set`: Replace the session state with the provided object.

### Structured Errors

* `error_summary`: Always required on failure. Safe for display to non-technical users.
* `error`: Optional structured data for the UI to handle specific error cases (e.g., highlighting fields).

### UI Elements (`outputs`)

Tool results are rendered as a list of UI objects:

* **notice:** `{"kind": "notice", "level": "info|warning|error", "message": "..."}`
* **markdown:** `{"kind": "markdown", "markdown": "..."}`
* **table:** `{"kind": "table", "title": "...", "columns": [...], "rows": [...]}`
* **json:** `{"kind": "json", "title": "...", "value": {...}}`
* **html_sandboxed:** `{"kind": "html_sandboxed", "html": "..."}`
* **vega_lite:** `{"kind": "vega_lite", "spec": {...}}`

### Developer Experience (DX)

### The Toolkit (`skriptoteket_toolkit.py`)

Always use the toolkit for a stable experience:

```python
from skriptoteket_toolkit import get_action_parts, read_inputs, read_settings

action_id, action_input, state = get_action_parts()
inputs = action_input if action_id else read_inputs()

### Get settings
settings = read_settings()
```

### Return Values

Your `run_tool` function can return:

1. A **string**: Treated as `html_sandboxed` output (backwards compatible).
2. A **dict**: Must follow the contract (can omit optional fields).

```python
def run_tool(input_dir, output_dir):
    return {
        "outputs": [{"kind": "markdown", "markdown": "# Success"}],
        "state_update": {"kind": "set", "state": {"step": 2}}
    }
```

### Scope And Boundaries

No separate material is recorded in the source snapshot.

### Evidence And Follow-Up

The source snapshot is the governing reference record.

## Facts And Semantics

The migrated source records no separate statement for this section.

## Decisions And Interpretation

The migrated source records no separate statement for this section.
