"""
Extrahera vårdnadshavares e-postadresser från en klasslista (CSV/XLSX).

Vanligt användningsområden:
- Du har en export från IST (eller liknande system) med elevrader.
- I exporten finns en eller flera kolumner med vårdnadshavares e‑postadresser.
- Du vill snabbt få ut en semikolonseparerad lista som går att klistra in i Outlooks BCC-fält.

Runner-kontrakt:
- Entrypoint: run_tool(input_path: str, output_dir: str) -> str
- Input: CSV eller XLSX med rubrikrad
- Output: HTML (för UI) + en fil `emails_<timestamp>.txt` som artifact
"""

import re
from collections.abc import Iterable
from datetime import datetime, timezone
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
    total_email_occurrences = 0
    col_email_counts: dict[str, int] = {}

    for col in ordered_cols:
        idx = col_indices[col]
        cells = [row[idx] for row in data_rows if idx < len(row)]
        emails = harvest_emails_from_cells(cells)
        total_email_occurrences += len(emails)
        new_emails = [e for e in emails if e not in all_emails]
        col_email_counts[col] = len(new_emails)
        all_emails.extend(new_emails)

    duplicates_removed = total_email_occurrences - len(all_emails)

    if not all_emails:
        return f"""
        <div class="tool-result">
            <div class="alert alert-warning">
                <strong>Inga e‑postadresser hittades</strong>
            </div>
            <p>Filen innehöll <strong>{len(data_rows)}</strong> rader men inga giltiga
            e‑postadresser kunde extraheras.</p>
            <details>
                <summary>Kolumner som genomsöktes</summary>
                <ul>
                    {"".join(f"<li>{col}</li>" for col in headers[:10])}
                    {"<li>...</li>" if len(headers) > 10 else ""}
                </ul>
            </details>
            <p><small>Tips: Kontrollera att filen innehåller kolumner med e‑postadresser
            (t.ex. "Vårdnadshavare e-post", "Parent email").</small></p>
        </div>
        """

    email_string = ";".join(all_emails)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    artifact_name = f"emails_{timestamp}.txt"
    artifact_path = output / artifact_name
    artifact_path.write_text(email_string, encoding="utf-8")

    stats_rows = "".join(
        f"<tr><td>{col}</td><td>{count}</td></tr>"
        for col, count in col_email_counts.items()
        if count > 0
    )

    dup_info = (
        f"<br><small>({duplicates_removed} dubbletter filtrerades bort)</small>"
        if duplicates_removed > 0
        else ""
    )

    return f"""
    <div class="tool-result">
        <div class="alert alert-success">
            <strong>{len(all_emails)}</strong> unika e‑postadresser extraherades
            från <strong>{len(data_rows)}</strong> rader.{dup_info}
        </div>

        <h4>E‑postadresser (semikolonseparerade)</h4>
        <textarea id="email-output" readonly
            style="width:100%; min-height:100px; font-family:monospace;
                   padding:8px; border-radius:4px;">{email_string}</textarea>

        <div style="margin-top:12px;">
            <button type="button" class="btn btn-primary"
                    data-huleedu-copy-target="email-output"
                    data-huleedu-copy-success="✓ Kopierat!">
                📋 Kopiera till urklipp
            </button>
        </div>
        <p style="margin-top:8px;">
            <small>Filen <code>{artifact_name}</code> sparades som artifact.</small>
        </p>

        <details style="margin-top:16px;">
            <summary>Statistik per kolumn</summary>
            <table class="table" style="margin-top:8px;">
                <thead>
                    <tr><th>Kolumn</th><th>Nya e‑postadresser</th></tr>
                </thead>
                <tbody>
                    {stats_rows}
                </tbody>
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
