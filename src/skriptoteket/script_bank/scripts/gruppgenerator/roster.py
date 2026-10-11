"""Roster parsing: class files (CSV/XLSX), saved classes and previous groups."""

from __future__ import annotations

import csv
import json
import re
from collections.abc import Mapping
from pathlib import Path

from skriptoteket_toolkit import list_input_files

SUPPORTED_ROSTER_SUFFIXES = {".csv", ".xlsx"}


def _normalize_name(value: str) -> str:
    return " ".join(value.strip().split())


def dedupe_names(names: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for name in names:
        cleaned = _normalize_name(name)
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(cleaned)
    return result


def _detect_name_column(headers: list[str]) -> int:
    for idx, header in enumerate(headers):
        candidate = header.strip().casefold()
        if "namn" in candidate or "name" in candidate:
            return idx
    return 0


def _read_csv_rows(path: Path) -> list[list[str]]:
    content = path.read_text(encoding="utf-8-sig")
    # Try sniffing, fallback to common delimiters
    for delimiter in [",", ";", "\t"]:
        try:
            reader = csv.reader(content.splitlines(), delimiter=delimiter)
            rows = list(reader)
        except csv.Error:
            continue
        if rows and len(rows[0]) > 1:
            return rows
    # Fallback default
    reader = csv.reader(content.splitlines())
    return list(reader)


def _read_xlsx_rows(path: Path) -> list[list[str]]:
    try:
        from openpyxl import load_workbook
    except ImportError:
        return []

    try:
        wb = load_workbook(path, read_only=True, data_only=True)
        ws = wb.active
        if ws is None:
            wb.close()
            return []
        rows = [[str(cell.value or "").strip() for cell in row] for row in ws.iter_rows()]
        wb.close()
        return rows
    except Exception:
        return []


def _extract_names_from_rows(rows: list[list[str]]) -> list[str]:
    if not rows:
        return []
    headers = rows[0]
    column_index = _detect_name_column(headers)
    names = []
    for row in rows[1:]:
        if column_index >= len(row):
            continue
        names.append(row[column_index])
    return dedupe_names(names)


def parse_roster_file(path: Path) -> tuple[list[str], str | None]:
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_ROSTER_SUFFIXES:
        return ([], f"Filtypen '{suffix}' stöds inte. Använd .csv eller .xlsx.")

    if suffix == ".xlsx":
        rows = _read_xlsx_rows(path)
        if not rows:
            return ([], "Kunde inte läsa Excel-filen (openpyxl saknas eller filen är tom/trasig).")
        return (_extract_names_from_rows(rows), None)

    rows = _read_csv_rows(path)
    if not rows:
        return ([], "CSV-filen verkar vara tom eller oläslig.")
    return (_extract_names_from_rows(rows), None)


def parse_saved_classes(settings: Mapping[str, object]) -> tuple[dict[str, list[str]], str | None]:
    raw = settings.get("saved_classes_json", "")

    # Also look for session-promoted classes
    session_classes: dict[str, list[str]] = {}
    for item in list_input_files():
        if item["name"] == "session_classes.json":
            try:
                data = json.loads(Path(item["path"]).read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    for k, v in data.items():
                        if isinstance(v, list):
                            session_classes[str(k)] = [str(i) for i in v]
            except Exception:
                pass

    if raw is None:
        return (session_classes, None)

    payload: dict[str, object] = {}
    if isinstance(raw, dict):
        payload = raw
    elif isinstance(raw, str):
        if not raw.strip():
            return (session_classes, None)
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return (session_classes, "Sparade klasser (JSON) i settings innehåller ogiltig JSON.")
    else:
        return (
            session_classes,
            "Sparade klasser (JSON) i settings måste vara text eller ett JSON-objekt.",
        )

    if not isinstance(payload, dict):
        return (session_classes, "Sparade klasser (JSON) i settings måste vara ett objekt.")

    classes: dict[str, list[str]] = dict(session_classes)
    for key, value in payload.items():
        if not isinstance(key, str):
            continue
        if isinstance(value, list):
            names = [str(item) for item in value if str(item).strip()]
            classes[key.strip()] = dedupe_names(names)
    return (classes, None)


def parse_previous_groups(raw: str) -> tuple[list[list[str]], str | None]:
    if not raw.strip():
        return ([], None)

    # Try JSON first
    try:
        payload = json.loads(raw)
        if isinstance(payload, list):
            json_groups: list[list[str]] = []
            for item in payload:
                if isinstance(item, list):
                    clean_group = [str(entry).strip() for entry in item if str(entry).strip()]
                    if clean_group:
                        json_groups.append(clean_group)
            return (json_groups, None)
    except json.JSONDecodeError:
        pass

    # Fallback: simple text parsing (lines with comma/semicolon)
    groups: list[list[str]] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        parts = [p.strip() for p in re.split(r"[;,]", line) if p.strip()]
        if parts:
            groups.append(parts)

    if not groups:
        return ([], "Kunde inte tolka tidigare grupper (varken som JSON eller text).")
    return (groups, None)


def select_roster_file(input_dir: Path) -> Path | None:
    manifest_files = list_input_files()
    for item in manifest_files:
        path = Path(str(item["path"]))
        if path.suffix.lower() in SUPPORTED_ROSTER_SUFFIXES:
            return path

    if not input_dir.is_dir():
        return None
    for path in sorted(input_dir.glob("*")):
        if path.suffix.lower() in SUPPORTED_ROSTER_SUFFIXES and path.is_file():
            return path
    return None
