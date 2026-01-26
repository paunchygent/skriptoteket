---
type: reference
id: REF-runner-contract-v3
title: "Runner Contract V3 - Structured Results, State & Promotions"
status: active
owners: ["agents"]
created: 2026-01-26
topic: "scripting"
---

## Overview

Runner Contract V3 is the authoritative interface between the Skriptoteket platform and tool scripts running in Docker. It provides structured error handling, unambiguous state updates, and support for session promotions.

Related documents:

* ADR-0065: Runner contract v3
* ADR-0063: Runner request envelope v1
* ADR-0064: File references and resolver

## Execution Environment

* **OS:** Debian-based (Docker)
* **Python:** 3.13+
* **Network:** Disabled (`--network none`)
* **Filesystem:** Read-only except for `/work` and `/tmp`.
* **Work Directory:** `/work`
* **Entrypoint:** Default is `run_tool(input_dir: str, output_dir: str) -> dict | str`.

## Request Inputs (Environment)

The platform provides inputs via environment variables and files in `/work`:

| Variable | Description |
| :------- | :---------- |
| `SKRIPTOTEKET_INPUTS` | JSON object containing form inputs (strings, integers, etc.). |
| `SKRIPTOTEKET_INPUT_DIR` | Path to input files directory (default: `/work/input`). |
| `SKRIPTOTEKET_INPUT_MANIFEST` | JSON manifest of all available input files. |
| `SKRIPTOTEKET_ACTION` | JSON object for multi-step tools `{action_id, input, state}`. |
| `SKRIPTOTEKET_MEMORY_PATH` | Path to memory JSON file containing `settings`. |

**Recommendation:** Use `skriptoteket_toolkit` instead of reading these directly.

## Result Contract (`result.json`)

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

## UI Elements (`outputs`)

Tool results are rendered as a list of UI objects:

* **notice:** `{"kind": "notice", "level": "info|warning|error", "message": "..."}`
* **markdown:** `{"kind": "markdown", "markdown": "..."}`
* **table:** `{"kind": "table", "title": "...", "columns": [...], "rows": [...]}`
* **json:** `{"kind": "json", "title": "...", "value": {...}}`
* **html_sandboxed:** `{"kind": "html_sandboxed", "html": "..."}`
* **vega_lite:** `{"kind": "vega_lite", "spec": {...}}`

## Developer Experience (DX)

### The Toolkit (`skriptoteket_toolkit.py`)

Always use the toolkit for a stable experience:

```python
from skriptoteket_toolkit import get_action_parts, read_inputs, read_settings

# Get inputs (initial or action)
action_id, action_input, state = get_action_parts()
inputs = action_input if action_id else read_inputs()

# Get settings
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
