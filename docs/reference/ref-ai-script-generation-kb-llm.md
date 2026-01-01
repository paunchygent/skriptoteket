---
type: reference
id: REF-ai-script-generation-kb-llm
title: "AI Script Generation KB (LLM)"
status: active
owners: "agents"
created: 2025-12-31
topic: "scripting"
---

Short, LLM-optimized rules for Skriptoteket. Use this **as the system prompt KB**
instead of the full human reference doc. Keep this file **compact** and focused
on execution constraints.

## Usage

- Audience: system prompt for LLMs used in inline completions and edit suggestions.
- Do not show to end users.
- Keep under ~1-2k tokens; prefer bullet rules and short examples.
- If constraints change, update this file and the human KB separately.

## Hard requirements

- **Entrypoint:** `def run_tool(input_dir: str, output_dir: str) -> dict` (HTML string allowed but discouraged).
- **Return Contract v2:**
  - `outputs`: list
  - `next_actions`: list (can be empty)
  - `state`: dict or `None`
- **No network access.** Execution uses `--network none`.
- **Artifacts must stay under `output_dir`.** No absolute paths, no `..`.
- **Prefer Swedish for user-facing messages.**

## Input & environment

- **Input files:** read from `SKRIPTOTEKET_INPUT_MANIFEST` (JSON) or `input_dir`.
- **Memory:** `SKRIPTOTEKET_MEMORY_PATH` (default `/work/memory.json`) may contain
  user settings under `memory["settings"]`.
- **Filesystem:** read-only except `/work` and `/tmp`.
- **Resources:** timeout 60s (sandbox) / 120s (prod), CPU 1, memory 1 GB.

## Output types (short)

- **notice:** `{"kind":"notice","level":"info|warning|error","message":"..."}`
  `message` max 8 KB.
- **markdown:** `{"kind":"markdown","markdown":"..."}`
  max 64 KB.
- **table:** `{"kind":"table","title":?, "columns":[{key,label}], "rows":[...]}`
  - max 40 columns, 750 rows, 512 bytes per cell
- **json:** `{"kind":"json","title":?, "value":{...}}`
  - max 96 KB, depth <= 10, 1000 keys/object, 2000 items/array
- **html_sandboxed:** `{"kind":"html_sandboxed","html":"..."}`
  max 96 KB (no JS access)

**Global limits:** max 50 outputs, total UI payload max 256 KB (standard profile).

## Artifacts

- Write files to `output_dir`; runner collects everything there.
- Retention ~7 days (default).

## Error handling

- **Expected errors:** return a notice with `level:"error"` (run can still succeed).
- **Abort with a clear error:** `raise ToolUserError("...")`
  - Message becomes `error_summary`.
  - No secrets, paths, or stacktraces.

## Minimal template (recommended)

```python
import json
import os
from pathlib import Path

def run_tool(input_dir: str, output_dir: str) -> dict:
    manifest_raw = os.environ.get("SKRIPTOTEKET_INPUT_MANIFEST", "")
    manifest = json.loads(manifest_raw) if manifest_raw else {}
    files = [Path(f["path"]) for f in manifest.get("files", [])]

    if not files:
        return {
            "outputs": [{"kind":"notice","level":"error","message":"Ingen fil uppladdad"}],
            "next_actions": [],
            "state": None,
        }

    # Bearbeta...

    return {
        "outputs": [{"kind":"notice","level":"info","message":"Klar!"}],
        "next_actions": [],
        "state": None,
    }
```
