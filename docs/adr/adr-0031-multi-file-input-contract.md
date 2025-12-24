---
type: adr
id: ADR-0031
title: "Multi-file input contract"
status: accepted
owners: "agents"
deciders: ["olof"]
created: 2025-12-21
updated: 2025-12-24
links: ["PRD-script-hub-v0.2", "EPIC-12", "ADR-0013", "ADR-0015"]
---

## Context

The current execution model (ADR-0013) injects a **single input file** into the runner container:

- User uploads one file via `<input type="file">`
- Runner receives `input_filename` + `input_bytes`
- Script discovers input files via `SKRIPTOTEKET_INPUT_MANIFEST` environment variable

This limitation prevents tools that need to correlate multiple files, such as:

- HTML files with external CSS/JS assets
- Budget reports cross-referenced with staff lists
- Student rosters compared with previous term's data

PRD-script-hub-v0.2 defines "Advanced Input Handling" as a v0.2 feature requiring multi-file support.

## Decision

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

### 4) Input manifest: `SKRIPTOTEKET_INPUT_MANIFEST`

A new environment variable provides JSON metadata about all input files:

```json
{
  "files": [
    {"name": "file1.html", "path": "/work/input/file1.html", "bytes": 6257},
    {"name": "file2.css", "path": "/work/input/file2.css", "bytes": 1024}
  ]
}
```

Scripts can parse this to discover available inputs with metadata.

### 5) Input directory: `SKRIPTOTEKET_INPUT_DIR`

The runner sets:

```bash
SKRIPTOTEKET_INPUT_DIR=/work/input
SKRIPTOTEKET_INPUT_MANIFEST={"files":[...all files...]}
```

The runner also passes `SKRIPTOTEKET_INPUT_DIR` as the first argument to the tool entrypoint.

### 6) Script patterns

**Single-file script (select first file from manifest):**

```python
import json
import os
from pathlib import Path

def run_tool(input_dir: str, output_dir: str) -> dict:
    manifest = json.loads(os.environ.get("SKRIPTOTEKET_INPUT_MANIFEST", "{}"))
    files = [Path(f["path"]) for f in manifest.get("files", [])]
    path = files[0]
    # Process path...
```

**Multi-file script:**

```python
import json
import os
from pathlib import Path

def run_tool(input_dir: str, output_dir: str) -> dict:
    # Option A: Use manifest
    manifest = json.loads(os.environ.get("SKRIPTOTEKET_INPUT_MANIFEST", "{}"))
    files = {Path(f["name"]).suffix.lower(): Path(f["path"]) for f in manifest.get("files", [])}
    html_file = files.get(".html")
    css_file = files.get(".css")

    # Option B: Discover from input directory
    input_dir_path = Path(input_dir)
    files = list(input_dir_path.iterdir())
```

## Consequences

### Benefits

- Enables complex multi-file workflows (HTML+CSS, cross-file comparison)
- Manifest provides rich metadata for advanced use cases
- Consistent with existing `/work/input/` layout

### Tradeoffs / Risks

- Increased upload size may hit timeouts (mitigate: per-file and total size caps)
- Filename collisions if user uploads files with same name (mitigate: reject duplicates after sanitization)
- More complex error handling for partial upload failures
- Knowledge base needs updated patterns for LLM script generation
