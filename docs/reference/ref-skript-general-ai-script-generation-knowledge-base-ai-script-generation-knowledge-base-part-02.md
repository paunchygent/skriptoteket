---
type: reference
id: REF-SKRIPT-GENERAL-ai-script-generation-knowledge-base-PART-02
title: AI Script Generation Knowledge Base — part 02
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
root: REF-SKRIPT-GENERAL-ai-script-generation-knowledge-base
part: 2
---

```python
import csv
from pathlib import Path
from skriptoteket_toolkit import list_input_files

def run_tool(input_dir: str, output_dir: str) -> dict:
    files = [Path(f["path"]) for f in list_input_files()]

    if not files:
        return {
            "outputs": [{"kind": "notice", "level": "error", "message": "Ingen fil uppladdad"}],
            "next_actions": [],
            "state": None
        }

    path = files[0]

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
from skriptoteket_toolkit import list_input_files

def run_tool(input_dir: str, output_dir: str) -> dict:
    files = [Path(f["path"]) for f in list_input_files()]
    path = files[0] if files else None

    if path is None:
        return {
            "outputs": [{"kind": "notice", "level": "error", "message": "Ingen fil uppladdad"}],
            "next_actions": [],
            "state": None
        }

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

### 7.3 Multi-fil indata (manifest)

```python
from pathlib import Path
from skriptoteket_toolkit import list_input_files, read_input_manifest

def run_tool(input_dir: str, output_dir: str) -> dict:
    manifest = read_input_manifest()
    files = [Path(f["path"]) for f in list_input_files()]

    # Alternativ: lista alla filer i input-katalogen
    input_dir_path = Path(input_dir)
    all_files = list(input_dir_path.iterdir())

    return {
        "outputs": [
            {"kind": "notice", "level": "info", "message": f"Filer: {len(files)}"},
            {"kind": "json", "title": "input_manifest", "value": manifest},
        ],
        "next_actions": [],
        "state": None,
    }
```

### 7.4 Läsa per-användare-inställningar (memory.json)

```python
from skriptoteket_toolkit import read_settings

def run_tool(input_dir: str, output_dir: str) -> dict:
    settings = read_settings()
    theme_color = settings.get("theme_color", "#000000")

    return {
        "outputs": [
            {"kind": "notice", "level": "info", "message": f"theme_color={theme_color}"},
            {"kind": "json", "title": "settings", "value": settings},
        ],
        "next_actions": [],
        "state": None,
    }
```

### 7.5 Skapa PDF från HTML

```python
from pathlib import Path
from pdf_helper import save_as_pdf

def run_tool(input_dir: str, output_dir: str) -> dict:
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

    pdf_path = save_as_pdf(html_content, output_dir, "rapport.pdf")

    return {
        "outputs": [
            {"kind": "notice", "level": "info", "message": "PDF skapad!"},
            {"kind": "markdown", "markdown": f"Ladda ner **{Path(pdf_path).name}** ovan."}
        ],
        "next_actions": [],
        "state": None
    }
```

### 7.6 Använda pandas

```python
import pandas as pd
from pathlib import Path
from skriptoteket_toolkit import list_input_files

def run_tool(input_dir: str, output_dir: str) -> dict:
    files = [Path(f["path"]) for f in list_input_files()]
    path = files[0] if files else None

    if path is None:
        return {
            "outputs": [{"kind": "notice", "level": "error", "message": "Ingen fil uppladdad"}],
            "next_actions": [],
            "state": None
        }

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

### 8. Felhantering

### 8.1 Användarfel (förväntat)

Returnera ett felmeddelande via outputs:

```python
from pathlib import Path
from skriptoteket_toolkit import list_input_files

def run_tool(input_dir: str, output_dir: str) -> dict:
    files = [Path(f["path"]) for f in list_input_files()]
    path = files[0] if files else None

    if path is None:
        return {
            "outputs": [{"kind": "notice", "level": "error", "message": "Ingen fil uppladdad"}],
            "next_actions": [],
            "state": None
        }

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
def run_tool(input_dir: str, output_dir: str) -> dict:
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

### 8.4 ToolUserError (dedikerat undantag)

För rena felmeddelanden som inte behöver ett `outputs`-svar kan du använda `ToolUserError`:

```python
from tool_errors import ToolUserError
from pathlib import Path
from skriptoteket_toolkit import list_input_files

def run_tool(input_dir: str, output_dir: str) -> dict:
    files = [Path(f["path"]) for f in list_input_files()]
    path = files[0] if files else None

    if path is None:
        raise ToolUserError("Ingen fil uppladdad.")

    if path.stat().st_size > 10_000_000:
        raise ToolUserError("Filen är för stor (max 10 MB).")

    # Fortsätt bearbetning...
```

**Skillnad mot notice-error:**

| Metod | Status | Användning |
|-------|--------|------------|
| `raise ToolUserError(msg)` | `failed` | Avbryt körningen helt |
| Return med notice `level: error` | `succeeded` | Rapportera fel men fortsätt (t.ex. validera fler rader) |

**Regler:**

- Meddelandet visas som `error_summary` i resultatet
- Inga stacktraces, sökvägar eller hemligheter i meddelandet
- Använd svenska, tydliga meddelanden

---

### 9. Felmeddelanden och felsökning

### 9.1 Vanliga felmeddelanden

| Meddelande | Orsak | Lösning |
|------------|-------|---------|
| `Runner contract violation: empty path` | Artefakt med tom sökväg | Kontrollera att alla filer har giltiga namn |
| `Runner contract violation: absolute paths are not allowed` | Absolut sökväg i artefakt | Använd relativa sökvägar under output_dir |
| `Runner contract violation: path traversal is not allowed` | `..` i sökväg | Ta bort path traversal |
| `Runner contract violation: artifact paths must be under output/` | Artefakt utanför output/ | Skriv alla filer till output_dir |
| `Runner at capacity; retry.` | För många samtidiga körningar | Vänta och försök igen |
| `Entrypoint not found: run_tool` | Funktionen saknas | Definiera `def run_tool(input_dir, output_dir)` |

### 9.2 Felsökning via loggar

- **stdout**: Synlig i admin-vyn, dold för vanliga användare
- **stderr**: Synlig i admin-vyn, innehåller exception stacktraces

```python
import sys

def run_tool(input_dir: str, output_dir: str) -> dict:
    # Debug-utskrift (synlig i admin-vyn)
    print(f"Input dir: {input_dir}", file=sys.stdout)
    print(f"Output dir: {output_dir}", file=sys.stderr)

    # ...
```

### 9.3 Kör lokalt för testning

```bash
### Från skript-filen direkt
python script.py /path/to/input_dir /tmp/output

### Visa result.json manuellt
cat /tmp/output/result.json | python -m json.tool
```

---

### 10. Checklista för skriptskapande

### 10.1 Innan du börjar

- [ ] Vilken filtyp ska skriptet hantera? (CSV, XLSX, PDF, etc.)
- [ ] Vad är det önskade resultatet? (Statistik, konverterad fil, extraherad data)
- [ ] Behövs artefakter (nedladdningsbara filer)?

### 10.2 Under utveckling

- [ ] Definiera `run_tool(input_dir: str, output_dir: str) -> dict`
- [ ] Hitta filer via `list_input_files()` (scripts ska inte anta en “primary file path”)
- [ ] Hantera filtypsvalidering tidigt
- [ ] Returnera alltid en giltig dict med `outputs`, `next_actions`, `state`
- [ ] Skriv artefakter till `Path(output_dir)`
- [ ] Fånga förväntade fel och ge användarvänliga meddelanden

### 10.3 Innan publicering

- [ ] Testa med sandbox-körning
- [ ] Verifiera att artefakter skapas korrekt
- [ ] Kontrollera att alla outputs följer storleksbegränsningarna
- [ ] Granska felhantering för kantfall
