---
type: reference
id: REF-ai-script-generation-kb
title: "AI Script Generation Knowledge Base"
status: active
owners: "agents"
created: 2025-12-20
topic: "scripting"
---

Detta dokument innehåller all information som en AI-assistent behöver för att hjälpa användare skapa skript enligt Skriptotekets datakontrakt.

---

## 1. Översikt

Skriptoteket är en plattform för att köra Python-skript som bearbetar uppladdade filer (CSV, XLSX, PDF, DOCX, etc.) och returnerar strukturerade resultat till användaren.

**Nyckelkoncept:**

- Användaren laddar upp en fil
- Skriptet bearbetar filen
- Skriptet returnerar UI-element (tabeller, meddelanden, markdown) och/eller nedladdningsbara artefakter
- Skriptet körs i en isolerad Docker-container utan nätverksåtkomst

---

## 2. Skriptets grundstruktur

### 2.1 Entrypoint-funktionen

Varje skript MÅSTE definiera en funktion med denna signatur:

```python
def run_tool(input_path: str, output_dir: str) -> str | dict:
    """
    Parametrar:
    - input_path: Absolut sökväg till den uppladdade filen
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

def run_tool(input_path: str, output_dir: str) -> dict:
    """Bearbeta den uppladdade filen och returnera resultat."""

    # Läs input
    path = Path(input_path)

    # Bearbeta...

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

## 3. Output-kontrakt (Contract v2)

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

| Begränsning | Standardprofil | Kuraterad profil |
|-------------|----------------|------------------|
| Max antal outputs | 50 | 150 |
| UI payload total | 256 KB | 512 KB |

---

## 4. Artefakter (nedladdningsbara filer)

### 4.1 Skapa artefakter

Skriv filer till `output_dir`:

```python
from pathlib import Path
from datetime import datetime, timezone

def run_tool(input_path: str, output_dir: str) -> dict:
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

## 5. Tillgängliga bibliotek

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

## 6. Körmiljöns begränsningar

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

```
/work/
├── script.py          # Ditt skript
├── input/
│   └── <filnamn>      # Uppladdad fil
├── output/            # Artefakter sparas här
└── result.json        # Genereras av runner

/tmp/                  # Skrivbar tmpfs (256 MB)
/app/.venv/            # Python-miljön
```

**Miljövariabler:**
- `SKRIPTOTEKET_SCRIPT_PATH`: Sökväg till skriptet
- `SKRIPTOTEKET_ENTRYPOINT`: Funktionsnamnet att anropa
- `SKRIPTOTEKET_INPUT_PATH`: Sökväg till indata
- `SKRIPTOTEKET_OUTPUT_DIR`: Katalog för artefakter
- `SKRIPTOTEKET_RESULT_PATH`: Där result.json skrivs

---

## 7. Vanliga mönster

### 7.1 Läsa CSV-fil

```python
import csv
from pathlib import Path

def run_tool(input_path: str, output_dir: str) -> dict:
    path = Path(input_path)

    # Läs med autodetektering av separator
    content = path.read_text(encoding="utf-8-sig")

    for delimiter in [",", ";", "\t"]:
        reader = csv.reader(content.splitlines(), delimiter=delimiter)
        rows = list(reader)
        if rows and len(rows[0]) > 1:
            break

    if not rows:
        return {
            "outputs": [{"kind": "notice", "level": "error", "message": "Filen är tom"}],
            "next_actions": [],
            "state": None
        }

    headers = rows[0]
    data = rows[1:]

    # Bearbeta...
```

### 7.2 Läsa Excel-fil

```python
from pathlib import Path
import warnings
from openpyxl import load_workbook

def run_tool(input_path: str, output_dir: str) -> dict:
    path = Path(input_path)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        wb = load_workbook(path, read_only=True, data_only=True)

    ws = wb.active
    if ws is None:
        wb.close()
        return {
            "outputs": [{"kind": "notice", "level": "error", "message": "Ingen aktiv sida i Excel-filen"}],
            "next_actions": [],
            "state": None
        }

    rows = [[str(cell.value or "") for cell in row] for row in ws.iter_rows()]
    wb.close()

    # Bearbeta...
```

### 7.3 Skapa PDF från HTML

```python
from pathlib import Path
from weasyprint import HTML

def run_tool(input_path: str, output_dir: str) -> dict:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    html_content = """
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"><title>Rapport</title></head>
    <body>
        <h1>Min rapport</h1>
        <p>Innehåll här...</p>
    </body>
    </html>
    """

    pdf_path = output / "rapport.pdf"
    HTML(string=html_content).write_pdf(pdf_path)

    return {
        "outputs": [
            {"kind": "notice", "level": "info", "message": "PDF skapad!"},
            {"kind": "markdown", "markdown": f"Ladda ner **{pdf_path.name}** ovan."}
        ],
        "next_actions": [],
        "state": None
    }
```

### 7.4 Använda pandas

```python
import pandas as pd
from pathlib import Path

def run_tool(input_path: str, output_dir: str) -> dict:
    path = Path(input_path)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    # Läs baserat på filtyp
    suffix = path.suffix.lower()
    if suffix == ".xlsx":
        df = pd.read_excel(path)
    elif suffix in {".csv", ".txt"}:
        df = pd.read_csv(path, encoding="utf-8-sig")
    else:
        return {
            "outputs": [{"kind": "notice", "level": "error", "message": f"Okänd filtyp: {suffix}"}],
            "next_actions": [],
            "state": None
        }

    # Visa statistik
    stats_rows = [{"kolumn": col, "unika": int(df[col].nunique())} for col in df.columns]

    return {
        "outputs": [
            {"kind": "notice", "level": "info", "message": f"Läste {len(df)} rader"},
            {
                "kind": "table",
                "title": "Kolumnstatistik",
                "columns": [
                    {"key": "kolumn", "label": "Kolumn"},
                    {"key": "unika", "label": "Unika värden"}
                ],
                "rows": stats_rows
            }
        ],
        "next_actions": [],
        "state": None
    }
```

---

## 8. Felhantering

### 8.1 Användarfel (förväntat)

Returnera ett felmeddelande via outputs:

```python
def run_tool(input_path: str, output_dir: str) -> dict:
    path = Path(input_path)
    suffix = path.suffix.lower()

    if suffix not in {".csv", ".xlsx"}:
        return {
            "outputs": [
                {
                    "kind": "notice",
                    "level": "error",
                    "message": f"Filtypen '{suffix}' stöds inte. Använd .csv eller .xlsx."
                }
            ],
            "next_actions": [],
            "state": None
        }

    # Fortsätt bearbetning...
```

### 8.2 Oväntat fel (exception)

Om skriptet kastar ett undantag:
- Körstatus sätts till `"failed"`
- `error_summary` sätts till `"Tool execution failed ({ExceptionType})."`
- Stacktrace skrivs till `stderr` (synlig i admin-vyn)

```python
def run_tool(input_path: str, output_dir: str) -> dict:
    try:
        # Riskabel operation
        result = risky_operation()
    except SpecificError as e:
        # Fånga specifika fel och ge användarvänligt meddelande
        return {
            "outputs": [
                {"kind": "notice", "level": "error", "message": f"Kunde inte bearbeta: {e}"}
            ],
            "next_actions": [],
            "state": None
        }
    # Låt andra fel bubbla upp för att loggas i stderr
```

### 8.3 Timeout

Om skriptet överskrider tidsgränsen:
- Körstatus: `"timed_out"`
- `error_summary`: `"Execution timed out."`

---

## 9. Felmeddelanden och felsökning

### 9.1 Vanliga felmeddelanden

| Meddelande | Orsak | Lösning |
|------------|-------|---------|
| `Runner contract violation: empty path` | Artefakt med tom sökväg | Kontrollera att alla filer har giltiga namn |
| `Runner contract violation: absolute paths are not allowed` | Absolut sökväg i artefakt | Använd relativa sökvägar under output_dir |
| `Runner contract violation: path traversal is not allowed` | `..` i sökväg | Ta bort path traversal |
| `Runner contract violation: artifact paths must be under output/` | Artefakt utanför output/ | Skriv alla filer till output_dir |
| `Runner at capacity; retry.` | För många samtidiga körningar | Vänta och försök igen |
| `Entrypoint not found: run_tool` | Funktionen saknas | Definiera `def run_tool(input_path, output_dir)` |

### 9.2 Felsökning via loggar

- **stdout**: Synlig i admin-vyn, dold för vanliga användare
- **stderr**: Synlig i admin-vyn, innehåller exception stacktraces

```python
import sys

def run_tool(input_path: str, output_dir: str) -> dict:
    # Debug-utskrift (synlig i admin-vyn)
    print(f"Input: {input_path}", file=sys.stdout)
    print(f"Output dir: {output_dir}", file=sys.stderr)

    # ...
```

### 9.3 Kör lokalt för testning

```bash
# Från skript-filen direkt
python script.py /path/to/testfile.csv /tmp/output

# Visa result.json manuellt
cat /tmp/output/result.json | python -m json.tool
```

---

## 10. Checklista för skriptskapande

### 10.1 Innan du börjar

- [ ] Vilken filtyp ska skriptet hantera? (CSV, XLSX, PDF, etc.)
- [ ] Vad är det önskade resultatet? (Statistik, konverterad fil, extraherad data)
- [ ] Behövs artefakter (nedladdningsbara filer)?

### 10.2 Under utveckling

- [ ] Definiera `run_tool(input_path: str, output_dir: str) -> dict`
- [ ] Hantera filtypsvalidering tidigt
- [ ] Returnera alltid en giltig dict med `outputs`, `next_actions`, `state`
- [ ] Skriv artefakter till `Path(output_dir)`
- [ ] Fånga förväntade fel och ge användarvänliga meddelanden

### 10.3 Innan publicering

- [ ] Testa med sandbox-körning
- [ ] Verifiera att artefakter skapas korrekt
- [ ] Kontrollera att alla outputs följer storleksbegränsningarna
- [ ] Granska felhantering för kantfall

---

## 11. Snabbreferens: Contract v2 typer

```python
# Output-typer
OutputKind = Literal["notice", "markdown", "table", "json", "html_sandboxed"]
NoticeLevel = Literal["info", "warning", "error"]

# Notice
{"kind": "notice", "level": NoticeLevel, "message": str}

# Markdown
{"kind": "markdown", "markdown": str}

# Table
{
    "kind": "table",
    "title": str | None,
    "columns": [{"key": str, "label": str}, ...],
    "rows": [{"key1": value1, "key2": value2}, ...]  # value: str | int | float | bool | None
}

# JSON
{"kind": "json", "title": str | None, "value": JsonValue}

# HTML
{"kind": "html_sandboxed", "html": str}

# Returformat
{
    "outputs": list[Output],
    "next_actions": list[FormAction],  # Framtida: interaktiva formulär
    "state": dict | None               # Framtida: spara state mellan körningar
}
```

---

## 12. Fullständigt exempelskript

```python
"""
Extrahera e-postadresser från en CSV/XLSX-fil.

Användning:
1. Ladda upp en fil med kolumner som innehåller e-postadresser
2. Skriptet returnerar en semikolonseparerad lista

Runner-kontrakt:
- Entrypoint: run_tool(input_path: str, output_dir: str) -> dict
- Input: CSV eller XLSX
- Output: Notice + artefakt med e-postlista
"""

import re
from datetime import datetime, timezone
from pathlib import Path

EMAIL_RE = re.compile(r"([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,15})")


def read_file(path: Path) -> tuple[list[str], list[list[str]]]:
    """Läs CSV eller XLSX och returnera (headers, data_rows)."""
    suffix = path.suffix.lower()

    if suffix == ".xlsx":
        import warnings
        from openpyxl import load_workbook

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            wb = load_workbook(path, read_only=True, data_only=True)
        ws = wb.active
        if ws is None:
            wb.close()
            return [], []
        rows = [[str(cell.value or "") for cell in row] for row in ws.iter_rows()]
        wb.close()
        return (rows[0], rows[1:]) if rows else ([], [])

    elif suffix in {".csv", ".txt"}:
        import csv
        content = path.read_text(encoding="utf-8-sig")
        for delimiter in [",", ";", "\t"]:
            reader = csv.reader(content.splitlines(), delimiter=delimiter)
            rows = list(reader)
            if rows and len(rows[0]) > 1:
                return rows[0], rows[1:]
        return (rows[0], rows[1:]) if rows else ([], [])

    return [], []


def harvest_emails(cells: list[str]) -> list[str]:
    """Extrahera unika e-postadresser från en lista med celler."""
    seen = set()
    result = []
    for cell in cells:
        for match in EMAIL_RE.findall(str(cell)):
            email = match.lower()
            if email not in seen:
                seen.add(email)
                result.append(email)
    return result


def run_tool(input_path: str, output_dir: str) -> dict:
    """Entrypoint: extrahera e-postadresser från uppladdad fil."""
    path = Path(input_path)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    # Validera filtyp
    suffix = path.suffix.lower()
    if suffix not in {".csv", ".xlsx", ".txt"}:
        return {
            "outputs": [
                {
                    "kind": "notice",
                    "level": "error",
                    "message": f"Filtypen '{suffix}' stöds inte. Använd .csv eller .xlsx."
                }
            ],
            "next_actions": [],
            "state": None
        }

    # Läs fil
    headers, data_rows = read_file(path)

    if not headers:
        return {
            "outputs": [
                {
                    "kind": "notice",
                    "level": "error",
                    "message": "Filen verkar tom eller saknar kolumnrubriker."
                }
            ],
            "next_actions": [],
            "state": None
        }

    # Samla e-postadresser från alla kolumner
    all_cells = []
    for row in data_rows:
        all_cells.extend(row)

    emails = harvest_emails(all_cells)

    if not emails:
        return {
            "outputs": [
                {"kind": "notice", "level": "warning", "message": "Inga e-postadresser hittades."},
                {
                    "kind": "markdown",
                    "markdown": (
                        f"Filen innehöll **{len(data_rows)}** rader men inga giltiga "
                        f"e-postadresser kunde extraheras.\n\n"
                        f"*Tips: Kontrollera att filen innehåller e-postadresser.*"
                    )
                }
            ],
            "next_actions": [],
            "state": None
        }

    # Skapa artefakt
    email_string = ";".join(emails)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    artifact_name = f"emails_{timestamp}.txt"
    artifact_path = output / artifact_name
    artifact_path.write_text(email_string, encoding="utf-8")

    return {
        "outputs": [
            {
                "kind": "notice",
                "level": "info",
                "message": f"{len(emails)} unika e-postadresser extraherades från {len(data_rows)} rader."
            },
            {
                "kind": "markdown",
                "markdown": f"Ladda ner **{artifact_name}** och klistra in i BCC-fältet."
            }
        ],
        "next_actions": [],
        "state": None
    }


if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <input_file> <output_dir>")
        raise SystemExit(1)

    result = run_tool(sys.argv[1], sys.argv[2])
    print(json.dumps(result, indent=2, ensure_ascii=False))
```

---

## 13. Frågor att ställa användaren

När en användare vill skapa ett nytt skript, ställ följande frågor:

1. **Filtyp:** Vilken typ av fil ska skriptet bearbeta? (CSV, XLSX, PDF, Word, annat)
2. **Syfte:** Vad är målet med bearbetningen? (Extrahera data, transformera, analysera, generera rapport)
3. **Output-format:** Hur vill användaren se resultatet? (Tabell, nedladdningsbar fil, statistik)
4. **Kolumner/fält:** Finns det specifika kolumner eller fält som är viktiga?
5. **Valideringsregler:** Finns det kriterier för vad som är giltigt/ogiltigt data?
6. **Felhantering:** Hur ska skriptet hantera problem (tomma filer, felaktigt format)?
