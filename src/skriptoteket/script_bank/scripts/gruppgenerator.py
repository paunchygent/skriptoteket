"""
Gruppgeneratorn: skapa elevgrupper från klasslistor (CSV/XLSX).

- Stöd för sparade klasser via settings (memory.json)
- Valfri hänsyn till tidigare grupper (minska upprepade par)
"""

from __future__ import annotations

import csv
import json
import random
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from skriptoteket_toolkit import (  # type: ignore[import-not-found]
    list_input_files,
    read_inputs,
    read_settings,
)

SUPPORTED_ROSTER_SUFFIXES = {".csv", ".xlsx"}
DEFAULT_GROUP_SIZE = 3
MAX_SHUFFLES = 200


def _notice(level: str, message: str) -> dict[str, object]:
    return {"kind": "notice", "level": level, "message": message}


def _markdown(content: str) -> dict[str, object]:
    return {"kind": "markdown", "markdown": content}


def _table(title: str, rows: list[dict[str, object]]) -> dict[str, object]:
    return {
        "kind": "table",
        "title": title,
        "columns": [
            {"key": "group", "label": "Grupp"},
            {"key": "members", "label": "Elever"},
        ],
        "rows": rows,
    }


def _normalize_name(value: str) -> str:
    return " ".join(value.strip().split())


def _dedupe_names(names: list[str]) -> list[str]:
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
    for delimiter in [",", ";", "\t"]:
        try:
            reader = csv.reader(content.splitlines(), delimiter=delimiter)
            rows = list(reader)
        except csv.Error:
            continue
        if rows and len(rows[0]) > 1:
            return rows
    reader = csv.reader(content.splitlines())
    return list(reader)


def _read_xlsx_rows(path: Path) -> list[list[str]]:
    try:
        from openpyxl import load_workbook  # type: ignore
    except Exception:
        return []

    wb = load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    if ws is None:
        wb.close()
        return []
    rows = [[str(cell.value or "").strip() for cell in row] for row in ws.iter_rows()]
    wb.close()
    return rows


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
    return _dedupe_names(names)


def _parse_roster_file(path: Path) -> tuple[list[str], str | None]:
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_ROSTER_SUFFIXES:
        return ([], f"Filtypen '{suffix}' stöds inte. Använd .csv eller .xlsx.")

    if suffix == ".xlsx":
        rows = _read_xlsx_rows(path)
        if not rows:
            return ([], "Kunde inte läsa Excel-filen (openpyxl saknas eller tom fil).")
        return (_extract_names_from_rows(rows), None)

    rows = _read_csv_rows(path)
    if not rows:
        return ([], "CSV-filen är tom.")
    return (_extract_names_from_rows(rows), None)


def _parse_saved_classes(settings: dict[str, Any]) -> tuple[dict[str, list[str]], str | None]:
    raw = settings.get("saved_classes_json", "")
    if raw is None:
        return ({}, None)
    if isinstance(raw, dict):
        payload = raw
    elif isinstance(raw, str):
        if not raw.strip():
            return ({}, None)
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return ({}, "Sparade klasser (JSON) är ogiltig JSON.")
    else:
        return ({}, "Sparade klasser (JSON) måste vara text eller JSON.")

    if not isinstance(payload, dict):
        return ({}, "Sparade klasser (JSON) måste vara ett objekt med klassnamn som nycklar.")

    classes: dict[str, list[str]] = {}
    for key, value in payload.items():
        if not isinstance(key, str):
            continue
        if isinstance(value, list):
            names = [str(item) for item in value if str(item).strip()]
            classes[key.strip()] = _dedupe_names(names)
    return (classes, None)


def _parse_previous_groups(raw: str) -> tuple[list[list[str]], str | None]:
    if not raw.strip():
        return ([], None)
    try:
        payload = json.loads(raw)
        if isinstance(payload, list):
            groups = []
            for item in payload:
                if isinstance(item, list):
                    groups.append([str(entry) for entry in item if str(entry).strip()])
            return (groups, None)
    except json.JSONDecodeError:
        pass

    groups: list[list[str]] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        parts = [p.strip() for p in re.split(r"[;,]", line) if p.strip()]
        if parts:
            groups.append(parts)
    if not groups:
        return ([], "Kunde inte tolka tidigare grupper.")
    return (groups, None)


def _pairs_for_groups(groups: list[list[str]]) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for group in groups:
        cleaned = _dedupe_names(group)
        for idx, name in enumerate(cleaned):
            for other in cleaned[idx + 1 :]:
                a, b = sorted((name.casefold(), other.casefold()))
                pairs.add((a, b))
    return pairs


def _score_groups(groups: list[list[str]], previous_pairs: set[tuple[str, str]]) -> int:
    if not previous_pairs:
        return 0
    score = 0
    for group in groups:
        cleaned = _dedupe_names(group)
        for idx, name in enumerate(cleaned):
            for other in cleaned[idx + 1 :]:
                a, b = sorted((name.casefold(), other.casefold()))
                if (a, b) in previous_pairs:
                    score += 1
    return score


def _chunk_groups(students: list[str], group_size: int) -> list[list[str]]:
    return [students[i : i + group_size] for i in range(0, len(students), group_size)]


def _build_groups(
    students: list[str],
    group_size: int,
    previous_pairs: set[tuple[str, str]],
) -> tuple[list[list[str]], int]:
    if not students:
        return ([], 0)
    rng = random.Random()
    best_groups = []
    best_score = float("inf")
    attempts = MAX_SHUFFLES if previous_pairs else 1
    pool = students[:]
    for _ in range(attempts):
        rng.shuffle(pool)
        groups = _chunk_groups(pool, group_size)
        score = _score_groups(groups, previous_pairs)
        if score < best_score:
            best_score = score
            best_groups = [group[:] for group in groups]
            if score == 0:
                break
    return (best_groups, int(best_score if best_score != float("inf") else 0))


def _select_roster_file(input_dir: Path) -> Path | None:
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


def run_tool(input_dir: str, output_dir: str) -> dict:
    inputs = read_inputs()
    settings = read_settings()

    group_size = int(inputs.get("group_size") or settings.get("default_group_size") or 0)
    if group_size < 2:
        group_size = DEFAULT_GROUP_SIZE

    class_name = str(inputs.get("class_name") or "").strip()
    group_set_name = str(inputs.get("group_set_name") or "").strip()
    previous_groups_raw = str(inputs.get("previous_groups") or "")

    saved_classes, saved_error = _parse_saved_classes(settings)
    if saved_error:
        return {
            "outputs": [
                _notice("error", saved_error),
                _markdown(
                    "Kontrollera att **Sparade klasser (JSON)** i settings är ett JSON-objekt."
                ),
            ],
            "next_actions": [],
            "state": None,
        }

    roster_path = _select_roster_file(Path(input_dir))
    students: list[str] = []
    roster_error: str | None = None

    if roster_path is not None:
        students, roster_error = _parse_roster_file(roster_path)
        if not class_name:
            class_name = roster_path.stem
    elif class_name:
        students = saved_classes.get(class_name, [])
        if not students:
            roster_error = f"Hittade ingen sparad klass med namnet '{class_name}'."
    else:
        roster_error = (
            "Ingen klasslista hittades. Ladda upp en fil eller ange ett sparat klassnamn."
        )

    if roster_error:
        return {
            "outputs": [
                _notice("error", roster_error),
                _markdown(
                    "Tips: Lägg klasslistor i settings som JSON för att kunna återanvända dem."
                ),
            ],
            "next_actions": [],
            "state": None,
        }

    if group_size > len(students):
        return {
            "outputs": [
                _notice(
                    "error",
                    f"Gruppstorlek ({group_size}) är större än antalet elever ({len(students)}).",
                )
            ],
            "next_actions": [],
            "state": None,
        }

    previous_groups, previous_error = _parse_previous_groups(previous_groups_raw)
    previous_pairs = _pairs_for_groups(previous_groups)

    groups, repeats = _build_groups(students, group_size, previous_pairs)

    group_label = group_set_name or "Grupp"
    rows = []
    markdown_lines = [f"**{group_set_name or 'Gruppindelning'}**\n"]
    for idx, group in enumerate(groups, start=1):
        name = f"{group_label} {idx}".strip()
        members = ", ".join(group)
        rows.append({"group": name, "members": members})
        markdown_lines.append(f"{idx}. {members}")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    artifact_name = f"grupper_{timestamp}.txt"
    (output_path / artifact_name).write_text("\n".join(markdown_lines), encoding="utf-8")

    outputs: list[dict[str, object]] = [
        _notice(
            "info",
            f"Elever: {len(students)} | Gruppstorlek: {group_size} | Grupper: {len(groups)}",
        ),
        _markdown("\n".join(markdown_lines)),
        _table("Gruppindelning", rows),
        _notice("info", f"Artefakt skapad: {artifact_name}"),
    ]

    if previous_error:
        outputs.append(_notice("warning", previous_error))
    if previous_pairs:
        outputs.append(_notice("info", f"Upprepade par mot tidigare grupper: {repeats}"))

    if class_name and roster_path is not None:
        updated_classes = dict(saved_classes)
        updated_classes[class_name] = students
        outputs.append(
            _markdown("Spara klassen i **Settings** genom att kopiera JSON från nästa block.")
        )
        outputs.append(
            {
                "kind": "json",
                "title": "Sparade klasser (JSON)",
                "value": updated_classes,
            }
        )

    if saved_classes:
        outputs.append(
            _markdown("Tillgängliga sparade klasser: " + ", ".join(sorted(saved_classes.keys())))
        )

    return {"outputs": outputs, "next_actions": [], "state": None}
