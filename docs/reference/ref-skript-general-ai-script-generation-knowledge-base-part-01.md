---
type: reference
id: REF-SKRIPT-GENERAL-ai-script-generation-knowledge-base-PART-01
title: AI Script Generation Knowledge Base — part 01
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
root: REF-SKRIPT-GENERAL-ai-script-generation-knowledge-base
part: 1
---

## Overview

Detta dokument innehåller all information som en AI-assistent behöver för att hjälpa användare skapa skript enligt Skriptotekets datakontrakt.

---

### 1. Översikt

Skriptoteket är en plattform för att köra Python-skript som bearbetar uppladdade filer (CSV, XLSX, PDF, DOCX, etc.) och returnerar strukturerade resultat till användaren.

**Nyckelkoncept:**

- Användaren laddar upp en eller flera filer
- Skriptet bearbetar en eller flera filer
- Skriptet returnerar UI-element (tabeller, meddelanden, markdown) och/eller nedladdningsbara artefakter
- Skriptet körs i en isolerad Docker-container utan nätverksåtkomst

---

### 2. Skriptets grundstruktur

### 2.1 Entrypoint-funktionen

Varje skript MÅSTE definiera en funktion med denna signatur:

```python
def run_tool(input_dir: str, output_dir: str) -> str | dict:
    """
    Parametrar:
    - input_dir: Absolut sökväg till katalogen med uppladdade filer (/work/input)
    - output_dir: Katalog där skriptet kan skriva artefakter (filer att ladda ner)

    Returnerar:
    - En HTML-sträng (äldre format, renderas i sandboxad iframe)
    - ELLER en dict enligt Contract v2 (rekommenderat, se nedan)
    """
```

**Viktigt:** Funktionsnamnet är konfigurerat till `run_tool` som standard, men kan ändras i verktygets inställningar.

### 2.2 Minimal skriptmall

```python
from pathlib import Path
from skriptoteket_toolkit import get_action_parts, list_input_files, read_inputs, read_settings

def run_tool(input_dir: str, output_dir: str) -> dict:
    """Bearbeta den uppladdade filen och returnera resultat."""

    # Action-körning (next_actions) vs första körning (input_schema-formulär)
    action_id, action_input, state = get_action_parts()
    inputs = action_input if action_id else read_inputs()
    settings = read_settings()

    # Hitta filer via input manifest (deterministiskt; säkra defaultvärden)
    files = [Path(f["path"]) for f in list_input_files()]

    if not files:
        return {
            "outputs": [{"kind": "notice", "level": "error", "message": "Ingen fil uppladdad"}],
            "next_actions": [],
            "state": None
        }

    path = files[0]

    # Bearbeta...
    # Exempel: title = inputs.get("title")
    # Exempel: threshold = int(settings.get("threshold", 10))
    # Exempel: steg = int(state.get("step", 0))

    # Returnera resultat enligt Contract v2
    return {
        "outputs": [
            {
                "kind": "notice",
                "level": "info",
                "message": "Bearbetningen lyckades!"
            }
        ],
        "next_actions": [],
        "state": None
    }
```

---

### 3. Output-kontrakt (Contract v2)

Skriptet returnerar en dict med tre fält:

```python
{
    "outputs": [...],      # Lista med UI-element
    "next_actions": [...], # Lista med formulär för uppföljningsåtgärder
    "state": {...}         # Valfritt state att spara mellan körningar
}
```

### 3.1 Output-typer (outputs)

#### 3.1.1 Notice (meddelanden)

```python
{
    "kind": "notice",
    "level": "info",      # "info" | "warning" | "error"
    "message": "Texten som visas för användaren"
}
```

**Begränsningar:**

- `message`: Max 8 KB

#### 3.1.2 Markdown

```python
{
    "kind": "markdown",
    "markdown": "## Rubrik\n\nVanlig text med **fetstil** och *kursiv*."
}
```

**Begränsningar:**

- `markdown`: Max 64 KB

#### 3.1.3 Tabell

```python
{
    "kind": "table",
    "title": "Statistik per kolumn",  # Valfritt
    "columns": [
        {"key": "column", "label": "Kolumn"},
        {"key": "count", "label": "Antal"}
    ],
    "rows": [
        {"column": "Namn", "count": 42},
        {"column": "E-post", "count": 38}
    ]
}
```

**Begränsningar:**

- Max 40 kolumner
- Max 750 rader
- Varje cell: Max 512 bytes

#### 3.1.4 JSON

```python
{
    "kind": "json",
    "title": "Diagnostik",  # Valfritt
    "value": {"any": "json", "data": [1, 2, 3]}
}
```

**Begränsningar:**

- `value`: Max 96 KB
- Max djup: 10 nivåer
- Max 1000 nycklar per objekt
- Max 2000 element per array

#### 3.1.5 HTML (sandboxad)

```python
{
    "kind": "html_sandboxed",
    "html": "<p>Renderas i en sandboxad iframe</p>"
}
```

**Begränsningar:**

- `html`: Max 96 KB
- Renderas i iframe utan JavaScript-åtkomst till huvudsidan

### 3.2 Globala begränsningar för outputs

| Begränsning | Standardprofil | Utökad profil |
|-------------|----------------|------------------|
| Max antal outputs | 50 | 150 |
| UI payload total | 256 KB | 512 KB |

---

### 3.3 Actions (`next_actions`) + state (interaktiva flöden)

Contract v2 stödjer interaktiva verktyg via:

- `next_actions`: formulär som UI:t renderar som knappar + fält
- `state`: valfritt JSON-state som sparas mellan körningar och skickas tillbaka vid nästa action-körning

**Rekommenderad läsning i skriptet:**

- Använd `skriptoteket_toolkit.get_action_parts()` för att skilja på:
  - första körning (ingen action) → läs `read_inputs()`
  - action-körning → läs `action_input` + `state`

#### 3.3.1 Form actions (schema)

En form-action ser ut så här:

```python
{
    "action_id": "continue",
    "label": "Nästa steg",
    "kind": "form",
    "fields": [
        {"name": "note", "kind": "string", "label": "Anteckning (valfri)"},
    ],
    # v2.x: optional prefill (se nedan)
    "prefill": {"note": "Steg 1"},
}
```

#### 3.3.2 `prefill` (action defaults, Contract v2.x)

`prefill` är en optional map: `{[field_name]: JsonValue}`.

UI:t använder `prefill` som **initialvärden** när action-formuläret renderas.

**Validering (server-side):**

- Okända nycklar (som inte matchar ett `fields[].name`) är ogiltiga.
- Värdet måste matcha fältets `kind`:
  - `string` / `text` / `enum`: `string`
  - `integer` / `number`: `number`
  - `boolean`: `boolean`
  - `multi_enum`: `string[]`

Ogiltiga `prefill`-entries strippas deterministiskt, och servern lägger till en system-notis i `outputs[]` så att det blir
actionable för verktygsförfattaren (ingen “tyst” undefined behavior).

**UI-semantik:**

- Prefill är “initial-value only”: när användaren har ändrat ett värde ska UI:t inte skriva över det på re-render.

### 4. Artefakter (nedladdningsbara filer)

### 4.1 Skapa artefakter

Skriv filer till `output_dir`:

```python
from pathlib import Path
from datetime import datetime, timezone

def run_tool(input_dir: str, output_dir: str) -> dict:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    # Skapa en artefakt
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    artifact_path = output / f"rapport_{timestamp}.txt"
    artifact_path.write_text("Innehållet i filen", encoding="utf-8")

    return {
        "outputs": [
            {
                "kind": "notice",
                "level": "info",
                "message": "Rapporten skapades!"
            }
        ],
        "next_actions": [],
        "state": None
    }
```

### 4.2 Artefaktregler

- **Sökväg:** Alla artefakter måste ligga under `output_dir`
- **Ingen path traversal:** `..` är inte tillåtet i sökvägar
- **Retention:** Artefakter sparas i 7 dagar som standard
- **Automatisk upptäckt:** Runner samlar automatiskt in alla filer under `output_dir`

---

### 5. Tillgängliga bibliotek

Följande Python-bibliotek finns förinstallerade i körmiljön:

### 5.1 Databearbetning

| Bibliotek | Användning |
|-----------|------------|
| `pandas` | Läsa/manipulera CSV, Excel-data |
| `openpyxl` | Läsa/skriva XLSX-filer |
| `pypdf` | Läsa PDF-filer |
| `python-docx` | Läsa/skriva Word-dokument |

### 5.2 Dokumentgenerering

| Bibliotek | Användning |
|-----------|------------|
| `pypandoc` | Konvertera mellan dokumentformat |
| `weasyprint` | Skapa PDF från HTML/CSS |
| `jinja2` | Template-rendering |

### 5.3 Verktyg

| Bibliotek | Användning |
|-----------|------------|
| `pydantic` | Datavalidering |
| `aiohttp` | HTTP-klient (BLOCKERAD: nätverket är avstängt) |
| `structlog` | Strukturerad loggning |
| `pyyaml` | YAML-parsing |

### 5.4 Systemverktyg (via apt)

- `pandoc` - Dokumentkonvertering
- `libcairo2` - 2D-grafik (används av weasyprint)

---

### 6. Körmiljöns begränsningar

### 6.1 Resursbegränsningar

| Resurs | Sandbox | Produktion |
|--------|---------|------------|
| Timeout | 60 sekunder | 120 sekunder |
| CPU | 1 kärna | 1 kärna |
| Minne | 1 GB | 1 GB |
| Max processer | 256 | 256 |
| Tmpfs | 256 MB | 256 MB |

### 6.2 Säkerhetsbegränsningar

| Begränsning | Status |
|-------------|--------|
| Nätverksåtkomst | **BLOCKERAD** (`--network none`) |
| Läs filsystem | Read-only (utom /work, /tmp) |
| Root-privilegier | Körs som `runner`-användare |
| Capabilities | Alla droppade (`--cap-drop ALL`) |

### 6.3 Filsystemlayout i containern

```text
/work/
├── script.py          # Ditt skript
├── memory.json        # Per-användare “Tool Memory” (t.ex. settings)
├── input/
│   ├── <filnamn>      # Uppladdad fil (kan vara flera)
│   └── <filnamn-2>
├── output/            # Artefakter sparas här
└── result.json        # Genereras av runner

/tmp/                  # Skrivbar tmpfs (256 MB)
/app/.venv/            # Python-miljön
```

**Miljövariabler:**

- `SKRIPTOTEKET_SCRIPT_PATH`: Sökväg till skriptet
- `SKRIPTOTEKET_ENTRYPOINT`: Funktionsnamnet att anropa
- `SKRIPTOTEKET_INPUT_DIR`: Katalog med uppladdade filer (t.ex. `/work/input`)
- `SKRIPTOTEKET_INPUT_MANIFEST`: JSON med metadata för alla uppladdade filer
- `SKRIPTOTEKET_MEMORY_PATH`: Sökväg till `memory.json` (t.ex. `memory["settings"]`)
- `SKRIPTOTEKET_OUTPUT_DIR`: Katalog för artefakter
- `SKRIPTOTEKET_RESULT_PATH`: Där result.json skrivs

---

### 7. Vanliga mönster

### 7.1 Läsa CSV-fil
