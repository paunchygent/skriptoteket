---
type: story
id: ST-08-11
title: "Script editor intelligence Phase 2: Contract validation + security"
status: ready
owners: "agents"
created: 2025-12-24
epic: "EPIC-08"
acceptance_criteria:
  - "Given the user is inside a return dict, when typing, then contract keys (outputs, next_actions, state) appear in autocomplete"
  - "Given a script returns a dict missing 'outputs', when linting runs, then an info diagnostic appears"
  - "Given an output dict has invalid 'kind', when linting runs, then a warning appears listing valid kinds"
  - "Given a script imports 'requests', when linting runs, then an error appears about blocked network"
  - "Given a script uses 'subprocess.run', when linting runs, then a warning appears about sandbox limitations"
ui_impact: "Extends editor intelligence with contract validation and security warnings."
data_impact: "None - client-side only."
dependencies: ["ST-08-10"]
---

## Context

Phase 2 builds on Phase 1 (discoverability MVP) by adding contract validation and security warnings. These lint rules
catch common errors that would fail at runtime in the Docker sandbox.

## Technical Decisions

See [ADR-0035: Script editor intelligence architecture](../../adr/adr-0035-script-editor-intelligence-architecture.md).

## Scope

### Contract Completions

- Complete `outputs`, `next_actions`, `state` inside return dict literals
- Complete output kind values: `notice`, `markdown`, `table`, `json`, `html_sandboxed`
- Complete notice fields: `level`, `message` when `kind: "notice"`
- Complete level values: `info`, `warning`, `error`

### Contract Lint Rules

| Rule ID | Severity | Swedish Message |
|---------|----------|-----------------|
| `ST_CONTRACT_KEYS_MISSING` | info | Retur-dict saknar nycklar: outputs / next_actions / state. |
| `ST_CONTRACT_OUTPUTS_NOT_LIST` | error | `outputs` måste vara en lista (`[...]`). |
| `ST_CONTRACT_OUTPUT_KIND_MISSING` | warning | Ett output-objekt saknar "kind". |
| `ST_CONTRACT_OUTPUT_KIND_INVALID` | warning | Ogiltigt kind: "\<value\>". Tillåtna: notice, markdown, table, json, html_sandboxed. |
| `ST_NOTICE_FIELDS_MISSING` | warning | Notice saknar "level" eller "message". |
| `ST_NOTICE_LEVEL_INVALID` | warning | Notice level måste vara info/warning/error. |

### Security Lint Rules

| Rule ID | Severity | Swedish Message |
|---------|----------|-----------------|
| `ST_SECURITY_NETWORK_IMPORT` | error | Nätverksbibliotek stöds inte i sandbox (ingen nätverksåtkomst). |
| `ST_SECURITY_SHELL_EXEC` | warning | Undvik subprocess/os.system i sandbox. Använd rena Python-lösningar. |
| `ST_SECURITY_WRITE_OUTSIDE_OUTPUT` | warning | Skrivning utanför output_dir blir inte en artefakt. |

## Technical Notes

### Contract Validation Limitations

Only lint when patterns are confident:

- Detect `return { ... }` where returned object is a literal dict
- Extract top-level keys (string literal keys only)
- If `outputs` exists and is a list literal, iterate entries
- For each dict literal entry, check keys and `kind` string value

Treat `return "<html>"` as supported legacy output (HTML sandbox) and do not apply Contract v2 linting to string returns.

When return is dynamic (variable) or dict built across statements:

- Do not attempt deep inference (too noisy)
- Emit a single `hint` diagnostic when:
  - Entrypoint exists, and
  - Entrypoint contains at least one `return`, and
  - Entrypoint contains no literal dict returns and no string literal returns
  - Swedish: "Kunde inte verifiera Contract v2 eftersom returvärdet byggs dynamiskt. Kontrollera att du returnerar dict med outputs/next_actions/state."

### Security Detection

Network imports:

```python
# Detect both forms:
import requests
from requests import get
```

Blocked modules (reduce false positives):

- `aiohttp`, `requests`, `httpx`, `urllib3`
- `urllib.request` and `urlopen`-style usage (avoid flagging `urllib.parse`)

Shell execution:

```python
# Detect imports and calls:
import subprocess
subprocess.run(...)
os.system(...)
os.popen(...)
```

Writes outside `output_dir` (best-effort heuristic):

- Warn only on obvious absolute string literal writes outside `/work/output`
- Exclude `/tmp` (writable tmpfs) to reduce noise
- Do not attempt dataflow/path inference

### Context-Aware Completions

Use Lezer syntax tree context:

- If cursor is inside a dict literal that is immediately returned → complete contract keys
- If cursor is inside a dict literal that is inside `outputs` list → complete output fields
- If current dict has `"kind": "notice"` → complete `level`, `message`

## Files

### Modify

- `frontend/apps/skriptoteket/src/composables/editor/skriptoteketCompletions.ts`
- `frontend/apps/skriptoteket/src/composables/editor/skriptoteketLinter.ts`
- `frontend/apps/skriptoteket/src/composables/editor/skriptoteketMetadata.ts`
