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

**Rekommendation:** Använd alltid dessa helpers istället för att läsa/parsa `os.environ` själv. Det gör skript mer
robusta, mer förutsägbara vid fel (säkra defaultvärden), och enklare att stödja via editor-intelligence och AI.

```python
from skriptoteket_toolkit import get_action_parts, list_input_files, read_inputs, read_settings

inputs = read_inputs()                 # {} om saknas/ogiltig JSON
settings = read_settings()             # {} om saknas/ogiltig JSON
files = list_input_files()             # [] om saknas/ogiltig JSON
action_id, action_input, state = get_action_parts()  # (None, {}, {}) om ej action-körning
```

### Exempel: `next_actions` med `prefill` (Contract v2.x)

För interaktiva verktyg kan du returnera `next_actions` där varje action är ett formulär. Varje action kan dessutom ha
en optional `prefill`-map (`{[field_name]: JsonValue}`) som UI:t använder som **initialvärde** när formuläret renderas.

```python
from skriptoteket_toolkit import get_action_parts


def run_tool(input_dir: str, output_dir: str) -> dict:
    action_id, action_input, state = get_action_parts()
    raw_step = state.get("step")
    try:
        step = int(raw_step) if isinstance(raw_step, (int, str)) else 0
    except (TypeError, ValueError):
        step = 0

    if action_id == "continue":
        step += 1

    return {
        "outputs": [{"kind": "notice", "level": "info", "message": f"Steg = {step}"}],
        "next_actions": [
            {
                "action_id": "continue",
                "label": "Nästa steg",
                "kind": "form",
                "fields": [{"name": "note", "kind": "string", "label": "Anteckning (valfri)"}],
                "prefill": {"note": f"Steg {step + 1}"},
            }
        ],
        "state": {"step": step},
    }
```

**Viktigt:**

- `prefill` är “initial-value only” (användarens editeringar ska inte skrivas över).
- Servern validerar `prefill` mot `fields[]` (okända fält eller fel typ strippas deterministiskt och ger en system-notis).

Environmentvariabler:

- `SKRIPTOTEKET_INPUTS` (JSON object) – formulärvärden för initial körning.
- `SKRIPTOTEKET_INPUT_MANIFEST` (JSON) – listar filer i `/work/input/` via `files[].path`.
- `SKRIPTOTEKET_ACTION` (JSON object) – payload för action-körningar: `{action_id, input, state}`.
- `SKRIPTOTEKET_MEMORY_PATH` – sökväg till `memory.json` (JSON) med `memory["settings"]`.

---

Se `docs/reference/ref-ai-script-generation-kb.md` för fullständig dokumentation.
