---
type: adr
id: ADR-SKRIPT-0031
title: Multi-file input contract
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: accepted
deciders:
- olof
retired_ids:
- ADR-0031
---

## Context

Source: `docs/adr/adr-0031-multi-file-input-contract.md`. Multi-file input contract.

The current execution model (ADR-0013) injects a **single input file** into the runner container: - User uploads one file via `<input type="file">` - Runner receives `input_filename` + `input_bytes` - Script discovers input files via the request manifest (ADR-0063) and `/work/input/` This limitation prevents tools that need to correlate multiple files, such as: - HTML files with external CSS/JS assets - Budget reports cross-referenced with staff lists - Student rosters compared with previous term's data PRD-script-hub-v0.2 defines "Advanced Input Handling" as a v0.2 feature requiring multi-file support. Extend the runner input contract to support **multiple input files**. Scripts MUST use th

## Decision

The migrated ADR preserves the source decision and its accepted boundary. Source evidence is retained below.

## Non-Decisions

No new decision, implementation authority, or terminal-state promotion is introduced by this migration.

## Consequences

### Source evidence

### Context

The current execution model (ADR-0013) injects a **single input file** into the runner container:

- User uploads one file via `<input type="file">`
- Runner receives `input_filename` + `input_bytes`
- Script discovers input files via the request manifest (ADR-0063) and `/work/input/`

This limitation prevents tools that need to correlate multiple files, such as:

- HTML files with external CSS/JS assets
- Budget reports cross-referenced with staff lists
- Student rosters compared with previous term's data

PRD-script-hub-v0.2 defines "Advanced Input Handling" as a v0.2 feature requiring multi-file support.

### Decision

Extend the runner input contract to support **multiple input files**. Scripts MUST use the input manifest and the
`/work/input/` directory for input discovery (no single-file compatibility env var).

### 0) Filename rules and collisions

- Filenames are sanitized to a safe “file name only” form (no paths).
- If multiple uploaded files collide **after sanitization**, the request is rejected with a validation error instructing
  the user to rename files locally.

### 1) Frontend: Multiple file upload

The upload form accepts multiple files:

```html
<input type="file" name="files" multiple />
```

UI shows all selected files before submission.

### 2) Command layer: List of input artifacts

`RunActiveToolCommand` and `ExecuteToolVersionCommand` accept:

```python
input_files: list[tuple[str, bytes]]  # (filename, content) pairs
```

### 3) Runner container: All files in `/work/input/`

All uploaded files are placed in the input directory:

```
/work/input/
├── file1.html
├── file2.css
└── file3.js
```

### 4) Input manifest: request envelope (`/work/request.json`)

The request envelope provides JSON metadata about all staged input files under `files[]`:

```json
{
  "schema_version": 1,
  "inputs": { "values": {} },
  "action": null,
  "files": [{ "name": "file1.html", "path": "/work/input/file1.html", "bytes": 6257 }]
}
```

Scripts can parse this to discover available inputs with metadata.

### 5) Input directory: `SKRIPTOTEKET_INPUT_DIR`

The runner sets:

```bash
SKRIPTOTEKET_INPUT_DIR=/work/input
```

The runner also passes `SKRIPTOTEKET_INPUT_DIR` as the first argument to the tool entrypoint.

### 6) Script patterns

**Single-file script (select first file from manifest):**

```python
from pathlib import Path

from skriptoteket_toolkit import list_input_files

def run_tool(input_dir: str, output_dir: str) -> dict:
    files = [Path(f["path"]) for f in list_input_files()]
    path = files[0]
    # Process path...
```

**Multi-file script:**

```python
from pathlib import Path

from skriptoteket_toolkit import list_input_files

def run_tool(input_dir: str, output_dir: str) -> dict:
    # Option A: Use manifest
    files = {Path(f["name"]).suffix.lower(): Path(f["path"]) for f in list_input_files()}
    html_file = files.get(".html")
    css_file = files.get(".css")

    # Option B: Discover from input directory
    input_dir_path = Path(input_dir)
    files = list(input_dir_path.iterdir())
```

### Consequences

### Benefits

- Enables complex multi-file workflows (HTML+CSS, cross-file comparison)
- Manifest provides rich metadata for advanced use cases
- Consistent with existing `/work/input/` layout

### Tradeoffs / Risks

- Increased upload size may hit timeouts (mitigate: per-file and total size caps)
- Filename collisions if user uploads files with same name (mitigate: reject duplicates after sanitization)
- More complex error handling for partial upload failures
- Knowledge base needs updated patterns for LLM script generation
