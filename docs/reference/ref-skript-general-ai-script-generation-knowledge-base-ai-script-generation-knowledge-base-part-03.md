---
type: reference
id: REF-SKRIPT-GENERAL-ai-script-generation-knowledge-base-PART-03
title: AI Script Generation Knowledge Base — part 03
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
root: REF-SKRIPT-GENERAL-ai-script-generation-knowledge-base
part: 3
---

---

### 11. Snabbreferens: Contract v2 typer

```python
### Output-typer
OutputKind = Literal["notice", "markdown", "table", "json", "html_sandboxed"]
NoticeLevel = Literal["info", "warning", "error"]

### Notice
{"kind": "notice", "level": NoticeLevel, "message": str}

### Markdown
{"kind": "markdown", "markdown": str}

### Table
{
    "kind": "table",
    "title": str | None,
    "columns": [{"key": str, "label": str}, ...],
    "rows": [{"key1": value1, "key2": value2}, ...]  # value: str | int | float | bool | None
}

### JSON
{"kind": "json", "title": str | None, "value": JsonValue}

### HTML
{"kind": "html_sandboxed", "html": str}

### Form actions (next_actions)
{
    "action_id": str,
    "label": str,
    "kind": "form",
    "fields": list[dict],              # fält enligt UiActionField (string/text/integer/number/boolean/enum/multi_enum)
    "prefill": dict[str, JsonValue] | None,  # v2.x: optional defaults/prefill
}

### Returformat
{
    "outputs": list[Output],
    "next_actions": list[FormAction],  # Interaktiva formulär (contract v2)
    "state": dict | None               # Valfritt state mellan körningar (contract v2)
}
```

---

### 12. Fullständigt exempelskript

```python
"""
Extrahera e-postadresser från en CSV/XLSX-fil.

Användning:
1. Ladda upp en fil med kolumner som innehåller e-postadresser
2. Skriptet returnerar en semikolonseparerad lista

Runner-kontrakt:
- Entrypoint: run_tool(input_dir: str, output_dir: str) -> dict
- Input: CSV eller XLSX
- Output: Notice + artefakt med e-postlista
"""

import re
from datetime import datetime, timezone
from pathlib import Path

from skriptoteket_toolkit import list_input_files

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


def run_tool(input_dir: str, output_dir: str) -> dict:
    """Entrypoint: extrahera e-postadresser från uppladdad fil."""
    files = [Path(f["path"]) for f in list_input_files()]
    path = files[0] if files else None

    if path is None:
        return {
            "outputs": [
                {"kind": "notice", "level": "error", "message": "Ingen fil uppladdad."},
            ],
            "next_actions": [],
            "state": None,
        }

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
        print(f"Usage: {sys.argv[0]} <input_dir> <output_dir>")
        raise SystemExit(1)

    result = run_tool(sys.argv[1], sys.argv[2])
    print(json.dumps(result, indent=2, ensure_ascii=False))
```

---

### 13. Frågor att ställa användaren

När en användare vill skapa ett nytt skript, ställ följande frågor:

1. **Filtyp:** Vilken typ av fil ska skriptet bearbeta? (CSV, XLSX, PDF, Word, annat)
2. **Syfte:** Vad är målet med bearbetningen? (Extrahera data, transformera, analysera, generera rapport)
3. **Output-format:** Hur vill användaren se resultatet? (Tabell, nedladdningsbar fil, statistik)
4. **Kolumner/fält:** Finns det specifika kolumner eller fält som är viktiga?
5. **Valideringsregler:** Finns det kriterier för vad som är giltigt/ogiltigt data?
6. **Felhantering:** Hur ska skriptet hantera problem (tomma filer, felaktigt format)?

## Facts And Semantics

The source material below remains authoritative for this section.

## Decisions And Interpretation

The source material below remains authoritative for this section.
