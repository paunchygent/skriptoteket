"""
Extrahera vårdnadshavares e-postadresser från en klasslista (CSV/XLSX).

Vanligt användningsområden:
- Du har en export från IST (eller liknande system) med elevrader.
- I exporten finns en eller flera kolumner med vårdnadshavares e‑postadresser.
- Du vill snabbt få ut en semikolonseparerad lista som går att klistra in i Outlooks BCC-fält.

Runner-kontrakt:
- Entrypoint: run_tool(input_path: str, output_dir: str) -> str
- Input: CSV eller XLSX med rubrikrad
- Output: HTML (för UI) + en fil `emails.txt` som artifact
"""

import re
from collections.abc import Iterable
from pathlib import Path

EMAIL_RE = re.compile(r"([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,15})")

# Ledtrådar som ofta finns i kolumnrubriker (svenska + engelska varianter)
GUARDIAN_HINTS = [
    "vardnad",
    "vårdnad",
    "foralder",
    "förälder",
    "parent",
    "guardian",
    "guardians",
]
EMAIL_HINTS = [
    "e-post",
    "epost",
    "email",
    "e-mail",
    "mejl",
    "mail",
]


def _column_matches_hints(col: str, hints: list[str]) -> bool:
    col_lower = col.lower()
    return any(hint in col_lower for hint in hints)


def prioritized_columns(columns: list[str]) -> list[str]:
    """Returnera kolumner i prioriterad ordning för mejl-extrahering.

    Prioritet:
    1) Kolumner som matchar både vårdnadshavare- och mejl-ledtrådar
    2) Kolumner som matchar mejl-ledtrådar
    3) Kolumner som matchar vårdnadshavare-ledtrådar
    4) Alla andra kolumner (fallback)
    """
    guardian_email = [
        c
        for c in columns
        if _column_matches_hints(c, GUARDIAN_HINTS) and _column_matches_hints(c, EMAIL_HINTS)
    ]
    email_only = [
        c for c in columns if _column_matches_hints(c, EMAIL_HINTS) and c not in guardian_email
    ]
    guardian_only = [
        c for c in columns if _column_matches_hints(c, GUARDIAN_HINTS) and c not in guardian_email
    ]
    other = [c for c in columns if c not in guardian_email + email_only + guardian_only]

    return guardian_email + email_only + guardian_only + other


def harvest_emails_from_cells(cells: Iterable[str]) -> list[str]:
    """Plocka ut unika mejladresser från celler (normaliseras till lowercase)."""
    seen: set[str] = set()
    result: list[str] = []
    for cell in cells:
        if not cell:
            continue
        for match in EMAIL_RE.findall(str(cell)):
            email = match.lower()
            if email not in seen:
                seen.add(email)
                result.append(email)
    return result


def read_csv(path: Path) -> tuple[list[str], list[list[str]]]:
    """Läs CSV med enkel avgränsardetektering (komma, semikolon, tab)."""
    import csv

    content = path.read_text(encoding="utf-8-sig")

    for delimiter in [",", ";", "\t"]:
        try:
            reader = csv.reader(content.splitlines(), delimiter=delimiter)
            rows = list(reader)
            if rows and len(rows[0]) > 1:
                return rows[0], rows[1:]
        except csv.Error:
            continue

    reader = csv.reader(content.splitlines())
    rows = list(reader)
    return rows[0] if rows else [], rows[1:] if len(rows) > 1 else []


def read_xlsx(path: Path) -> tuple[list[str], list[list[str]]]:
    """Läs XLSX med openpyxl (första bladet)."""
    from openpyxl import load_workbook

    wb = load_workbook(path, read_only=True, data_only=True)
    ws = wb.active

    rows = [[str(cell.value or "") for cell in row] for row in ws.iter_rows()]
    wb.close()

    if not rows:
        return [], []
    return rows[0], rows[1:]


def run_tool(input_path: str, output_dir: str) -> str:
    """Entrypoint: extrahera vårdnadshavares mejl från en klasslista."""
    path = Path(input_path)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    suffix = path.suffix.lower()
    if suffix == ".xlsx":
        headers, data_rows = read_xlsx(path)
    elif suffix in {".csv", ".txt"}:
        headers, data_rows = read_csv(path)
    else:
        return f"<p class='error'>Filtypen '{suffix}' stöds inte. Använd .csv eller .xlsx.</p>"

    if not headers:
        return "<p class='error'>Filen verkar tom eller saknar kolumnrubriker.</p>"

    ordered_cols = prioritized_columns(headers)
    col_indices = {col: headers.index(col) for col in ordered_cols}

    all_emails: list[str] = []
    col_email_counts: dict[str, int] = {}

    for col in ordered_cols:
        idx = col_indices[col]
        cells = [row[idx] for row in data_rows if idx < len(row)]
        emails = harvest_emails_from_cells(cells)
        new_emails = [e for e in emails if e not in all_emails]
        col_email_counts[col] = len(new_emails)
        all_emails.extend(new_emails)

    email_string = ";".join(all_emails)

    artifact_path = output / "emails.txt"
    artifact_path.write_text(email_string, encoding="utf-8")

    stats_rows = "".join(
        f"<tr><td>{col}</td><td>{count}</td></tr>"
        for col, count in col_email_counts.items()
        if count > 0
    )

    return f"""
    <div style="font-family: system-ui, sans-serif;">
        <h3>Resultat</h3>
        <p><strong>{len(all_emails)}</strong> unika e‑postadresser hittades.</p>

        <h4>E‑postadresser (semikolonseparerade)</h4>
        <textarea readonly style="width:100%; min-height:100px; font-family:monospace;"
            onclick="this.select()">{email_string}</textarea>
        <p><small>Klicka i textrutan och tryck Ctrl+C för att kopiera.</small></p>

        <details>
            <summary>Statistik per kolumn</summary>
            <table border="1" cellpadding="4" style="border-collapse:collapse;">
                <tr><th>Kolumn</th><th>Nya e‑postadresser</th></tr>
                {stats_rows}
            </table>
        </details>
    </div>
    """


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <input_file> <output_dir>")
        raise SystemExit(1)

    print(run_tool(sys.argv[1], sys.argv[2]))
