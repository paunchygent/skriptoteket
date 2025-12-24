---
type: story
id: ST-08-12
title: "Script editor intelligence Phase 3: Best practices + polish"
status: ready
owners: "agents"
created: 2025-12-24
epic: "EPIC-08"
acceptance_criteria:
  - "Given a script raises ToolUserError without import, when linting runs, then an error appears"
  - "Given a script uses open() without encoding=, when linting runs, then an info hint appears"
  - "Given a script imports weasyprint.HTML directly, when linting runs, then an info hint suggests pdf_helper"
  - "Given a script writes to output_dir without mkdir, when linting runs, then an info hint appears"
ui_impact: "Completes editor intelligence with best-practice guidance."
data_impact: "None - client-side only."
dependencies: ["ST-08-11"]
---

## Context

Phase 3 adds best-practice lint rules that guide script authors toward robust patterns. These are lower-severity hints
(mostly `info`) that improve code quality without blocking execution.

## Technical Decisions

See [ADR-0035: Script editor intelligence architecture](../../adr/adr-0035-script-editor-intelligence-architecture.md).

## Scope

### Best Practice Lint Rules

| Rule ID | Severity | Swedish Message |
|---------|----------|-----------------|
| `ST_BESTPRACTICE_TOOLUSERERROR_IMPORT` | error | ToolUserError används men import saknas: `from tool_errors import ToolUserError` |
| `ST_BESTPRACTICE_ENCODING` | info | Ange `encoding="utf-8"` vid textläsning/skrivning. |
| `ST_BESTPRACTICE_WEASYPRINT_DIRECT` | info | Använd `pdf_helper.save_as_pdf` istället för `weasyprint.HTML` direkt. |
| `ST_BESTPRACTICE_MKDIR` | info | Skapa gärna kataloger innan du skriver filer (särskilt undermappar). |

### Detection Patterns

#### ToolUserError without import

Build imports table during analysis. If `ToolUserError` appears in a `raise` statement but no matching import exists:

```python
from tool_errors import ToolUserError  # Required
# OR
import tool_errors  # Also valid (tool_errors.ToolUserError)
```

#### Encoding parameter

Detect calls without `encoding=` keyword:

```python
open(path, "r")           # Missing encoding
open(path, "w")           # Missing encoding
Path(x).read_text()       # Missing encoding
Path(x).write_text(...)   # Missing encoding
```

Skip binary mode (`"rb"`, `"wb"`) - no encoding needed.

#### WeasyPrint direct usage

Detect patterns:

```python
from weasyprint import HTML           # Direct import
HTML(string=...).write_pdf(...)       # Direct usage
```

Suggest: "Använd `pdf_helper.save_as_pdf(html, output_dir, filename)` för enklare hantering."

#### Missing mkdir

Heuristic: detect file writes to paths under `output_dir` without a preceding `mkdir`:

```python
# No mkdir before write → info hint
(output / "subdir" / "file.txt").write_text(...)

# With mkdir → no hint
(output / "subdir").mkdir(parents=True, exist_ok=True)
(output / "subdir" / "file.txt").write_text(...)
```

This is a best-effort heuristic; false positives are acceptable at `info` severity.

## Optional Enhancements

### Quick-fix actions (future)

CodeMirror 6 supports quick-fix actions via lint diagnostics. Consider adding:

- "Lägg till import" for missing `ToolUserError` import
- "Lägg till encoding='utf-8'" for file operations

### Swedish lint panel phrases (future)

If full Swedish UI is required, use `EditorState.phrases` to translate built-in lint panel strings.

## Files

### Modify

- `frontend/apps/skriptoteket/src/composables/editor/skriptoteketLinter.ts`
- `frontend/apps/skriptoteket/src/composables/editor/skriptoteketMetadata.ts`
