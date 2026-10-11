"""
Gruppgeneratorn: skapa elevgrupper från klasslistor (CSV/XLSX).

- Stöd för sparade klasser via settings (memory.json)
- Valfri hänsyn till tidigare grupper (minska upprepade par)
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, NotRequired, TypedDict

from skriptoteket_toolkit import (
    get_action_parts,
    list_input_files,
    read_inputs,
    read_settings,
)

from .grouping import build_groups, pairs_for_groups
from .roster import (
    parse_previous_groups,
    parse_roster_file,
    parse_saved_classes,
    select_roster_file,
)

DEFAULT_GROUP_SIZE = 3


class ToolResult(TypedDict):
    outputs: list[dict[str, object]]
    next_actions: list[dict[str, object]]
    state_update: dict[str, object]
    promotions: NotRequired[dict[str, object]]


def _notice(level: Literal["info", "warning", "error"], message: str) -> dict[str, object]:
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


def _build_action_fields(saved_classes: dict[str, list[str]]) -> list[dict[str, object]]:
    fields: list[dict[str, object]] = []
    if saved_classes:
        options = [
            {"value": key, "label": key} for key in sorted(saved_classes.keys(), key=str.casefold)
        ]
        fields.append(
            {
                "name": "saved_class",
                "label": "Sparad klass (valfri)",
                "kind": "enum",
                "options": options,
            }
        )
    fields.extend(
        [
            {
                "name": "group_size",
                "label": "Gruppstorlek",
                "kind": "integer",
            },
            {
                "name": "class_name",
                "label": "Klassnamn (för sparad klass eller för att spara ny)",
                "kind": "string",
            },
            {
                "name": "group_set_name",
                "label": "Namn på gruppindelningen",
                "kind": "string",
            },
            {
                "name": "previous_groups_file",
                "label": "Välj tidigare grupper (från session/valv)",
                "kind": "file_ref",
                "min": 0,
                "max": 1,
            },
            {
                "name": "previous_groups",
                "label": "Klistra in tidigare grupper (valfritt om fil ej väljs)",
                "kind": "text",
            },
        ]
    )
    return fields


def _build_actions(saved_classes: dict[str, list[str]]) -> list[dict[str, object]]:
    return [
        {
            "action_id": "generate",
            "label": "Skapa grupper",
            "kind": "form",
            "fields": _build_action_fields(saved_classes),
        }
    ]


def run_tool(input_dir: str, output_dir: str) -> ToolResult:
    inputs_raw = read_inputs()
    settings_raw = read_settings()
    action_id, action_input_raw, _ = get_action_parts()

    inputs: Mapping[str, object] = inputs_raw if isinstance(inputs_raw, dict) else {}
    settings: Mapping[str, object] = settings_raw if isinstance(settings_raw, dict) else {}
    action_input: Mapping[str, object] = (
        action_input_raw if isinstance(action_input_raw, dict) else {}
    )

    payload = action_input if action_id == "generate" else inputs

    group_size_raw = payload.get("group_size") or settings.get("default_group_size") or 0
    if not isinstance(group_size_raw, int | float | str):
        raise TypeError(f"Ogiltig gruppstorlek: {group_size_raw!r}")
    group_size = int(group_size_raw)
    if group_size < 2:
        group_size = DEFAULT_GROUP_SIZE

    class_name = str(payload.get("class_name") or "").strip()
    group_set_name = str(payload.get("group_set_name") or "").strip()
    previous_groups_raw = str(payload.get("previous_groups") or "")

    # Strategy: Read previous groups from file if provided, else fallback to text field
    previous_groups_file_refs = payload.get("previous_groups_file")
    if isinstance(previous_groups_file_refs, list) and previous_groups_file_refs:
        # Take the first one (usually max=1 anyway)
        file_ref = previous_groups_file_refs[0]
        # In Contract V3, selected files are staged into input_dir
        # We find it by matching name in list_input_files
        for item in list_input_files():
            if item.get("ref") == file_ref:
                try:
                    previous_groups_raw = Path(item["path"]).read_text(encoding="utf-8")
                    break
                except Exception:
                    pass

    saved_classes, saved_error = parse_saved_classes(settings)
    if saved_error:
        saved_classes = {}

    roster_path = select_roster_file(Path(input_dir))

    # --- Initial State (No Action) ---
    if action_id is None:
        initial_outputs: list[dict[str, object]] = []
        if saved_error:
            initial_outputs.append(_notice("warning", saved_error))

        has_saved = bool(saved_classes)

        if roster_path is not None:
            preview_students, preview_error = parse_roster_file(roster_path)
            if preview_error:
                initial_outputs.append(_notice("error", preview_error))
            else:
                initial_outputs.append(
                    _notice(
                        "info", f"Hittade {len(preview_students)} elever i '{roster_path.name}'."
                    )
                )
                if preview_students:
                    preview = ", ".join(preview_students[:10])
                    if len(preview_students) > 10:
                        preview += "..."
                    initial_outputs.append(_markdown(f"**Exempel på namn:** {preview}"))
        elif has_saved:
            initial_outputs.append(
                _notice("info", "Inga filer uppladdade. Du kan välja en sparad klass nedan.")
            )
        else:
            initial_outputs.append(
                _notice(
                    "error",
                    "Ingen klasslista hittades. Ladda upp en fil eller spara klasser i settings.",
                )
            )

        initial_outputs.append(_markdown("Fyll i formuläret nedan och klicka **Skapa grupper**."))

        return {
            "outputs": initial_outputs,
            "next_actions": _build_actions(saved_classes),
            "state_update": {"kind": "no_change"},
        }

    # --- Handle Action ---
    if action_id != "generate":
        return {
            "outputs": [_notice("error", f"Okänd action_id: '{action_id}'.")],
            "next_actions": _build_actions(saved_classes),
            "state_update": {"kind": "no_change"},
        }

    selected_saved = str(payload.get("saved_class") or "").strip()
    students: list[str] = []
    roster_error: str | None = None
    source_label = ""

    # Strategy: 1. Selected Saved, 2. Matching Class Name (Saved), 3. Uploaded File
    if selected_saved and selected_saved in saved_classes:
        students = saved_classes[selected_saved]
        class_name = selected_saved
        source_label = f"Sparad klass: {selected_saved}"
    elif class_name and class_name in saved_classes:
        students = saved_classes[class_name]
        source_label = f"Sparad klass: {class_name}"
    elif roster_path is not None:
        students, roster_error = parse_roster_file(roster_path)
        if not class_name:
            class_name = roster_path.stem
        source_label = f"Uppladdad fil: {roster_path.name}"
    elif class_name:
        roster_error = f"Hittade ingen sparad klass med namnet '{class_name}'."
    else:
        roster_error = (
            "Ingen klasslista hittades. Ladda upp en fil eller ange ett sparat klassnamn."
        )

    if roster_error or not students:
        return {
            "outputs": [
                _notice("error", roster_error or "Inga elever hittades i klasslistan."),
                _markdown(
                    "Tips: Lägg klasslistor i settings (memory.json) för att återanvända dem."
                ),
            ],
            "next_actions": _build_actions(saved_classes),
            "state_update": {"kind": "no_change"},
        }

    if group_size > len(students):
        return {
            "outputs": [
                _notice(
                    "error",
                    f"Gruppstorlek ({group_size}) är större än antalet elever ({len(students)}).",
                )
            ],
            "next_actions": _build_actions(saved_classes),
            "state_update": {"kind": "no_change"},
        }

    previous_groups, previous_error = parse_previous_groups(previous_groups_raw)
    previous_pairs = pairs_for_groups(previous_groups)

    groups, repeats = build_groups(students, group_size, previous_pairs)

    group_label = group_set_name or "Grupp"
    rows: list[dict[str, object]] = []
    markdown_lines = [f"**{group_set_name or 'Gruppindelning'}**\n"]
    for idx, group in enumerate(groups, start=1):
        name = f"{group_label} {idx}".strip()
        members = ", ".join(group)
        rows.append({"group": name, "members": members})
        markdown_lines.append(f"{idx}. {members}")

    # Create artifacts and promotions
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    # Artifact 1: Group list (TXT)
    artifact_name = f"grupper_{timestamp}.txt"
    (output_path / artifact_name).write_text("\n".join(markdown_lines), encoding="utf-8")

    promotions: dict[str, object] = {}
    # If we have new/updated classes, promote them to the session
    if class_name and (roster_path is not None or students):
        updated_classes = dict(saved_classes)
        updated_classes[class_name] = students

        # Write to a hidden artifact for session promotion
        session_file = "session_classes.json"
        (output_path / session_file).write_text(json.dumps(updated_classes), encoding="utf-8")

        promotions = {
            "requests": [
                {
                    "kind": "session",
                    "name": session_file,
                    "source_path": f"output/{session_file}",
                }
            ]
        }

    outputs: list[dict[str, object]] = [
        _notice(
            "info", f"Elever: {len(students)} | Gruppstorlek: {group_size} | Grupper: {len(groups)}"
        ),
        _notice("info", source_label),
        _markdown("\n".join(markdown_lines)),
        _table("Gruppindelning", rows),
        _notice("info", f"Artefakt skapad: {artifact_name}"),
    ]

    if saved_error:
        outputs.append(_notice("warning", saved_error))
    if previous_error:
        outputs.append(_notice("warning", previous_error))
    if previous_pairs:
        outputs.append(_notice("info", f"Upprepade par mot tidigare grupper: {repeats}"))

    # Offer to save class if from file (for PERMANENT storage in Settings)
    if class_name and roster_path is not None:
        updated_classes = dict(saved_classes)
        updated_classes[class_name] = students
        outputs.append(
            _markdown(
                "Klassen har sparats **temporärt** för denna session. "
                "För att spara den **permanent**, kopiera JSON-blocket nedan till "
                "verktygets **Settings**."
            )
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

    result: ToolResult = {
        "outputs": outputs,
        "next_actions": _build_actions(saved_classes),
        "state_update": {"kind": "no_change"},
    }
    if promotions:
        result["promotions"] = promotions

    return result
