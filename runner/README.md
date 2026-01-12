# Runner Helpers

Moduler tillgängliga för verktygs-skript i körmiljön.

## pdf_helper

Renderar HTML till PDF med WeasyPrint.

```python
from pdf_helper import save_as_pdf

pdf_path = save_as_pdf(html_content, output_dir, "rapport.pdf")
```

**Parametrar:**

- `html` - HTML-sträng att rendera
- `output_dir` - Katalog för artefakter (från `run_tool`-signaturen)
- `filename` - Relativ sökväg, måste sluta med `.pdf`

**Returnerar:** Absolut sökväg till skapad PDF.

## tool_errors

Undantag för användarvänliga felmeddelanden.

```python
from tool_errors import ToolUserError

raise ToolUserError("Filtypen stöds inte.")
```

Meddelandet visas som `error_summary` utan stacktrace.

## skriptoteket_toolkit

Små, stabila hjälpfunktioner för att läsa Skriptotekets runner-env (inputs/manifest/action/memory) på ett säkert sätt.

```python
from skriptoteket_toolkit import get_action_parts, list_input_files, read_inputs, read_settings

inputs = read_inputs()                 # {} om saknas/ogiltig JSON
settings = read_settings()             # {} om saknas/ogiltig JSON
files = list_input_files()             # [] om saknas/ogiltig JSON
action_id, action_input, state = get_action_parts()  # (None, {}, {}) om ej action-körning
```

Environmentvariabler:

- `SKRIPTOTEKET_INPUTS` (JSON object) – formulärvärden för initial körning.
- `SKRIPTOTEKET_INPUT_MANIFEST` (JSON) – listar filer i `/work/input/` via `files[].path`.
- `SKRIPTOTEKET_ACTION` (JSON object) – payload för action-körningar: `{action_id, input, state}`.
- `SKRIPTOTEKET_MEMORY_PATH` – sökväg till `memory.json` (JSON) med `memory["settings"]`.

---

Se `docs/reference/ref-ai-script-generation-kb.md` för fullständig dokumentation.
