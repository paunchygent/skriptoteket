"""
Demo: Interaktiv körning med next_actions (contract v2).

Syfte:
- Testa SPA-flödet: upload → outputs/artifacts → next_actions → ny körning → …
- Hålla logik enkel och robust: första action behandlar state som tomt ({}).

Runner-kontrakt:
- Entrypoint: run_tool(input_dir: str, output_dir: str) -> dict
- Input: filer i /work/input/ (hämta filvägar via input manifest)
- Action input: SKRIPTOTEKET_ACTION (env JSON med {action_id, input, state})
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from skriptoteket_toolkit import (  # type: ignore[import-not-found]
    get_action_parts,
    list_input_files,
)


def _safe_int(value: object, default: int = 0) -> int:
    try:
        return int(value)  # noqa: PLC1901
    except (TypeError, ValueError):
        return default


def _write_artifact(*, output_dir: Path, name: str, content: str) -> str:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / name
    path.write_text(content, encoding="utf-8")
    return name


def _notice(level: str, message: str) -> dict:
    return {"kind": "notice", "level": level, "message": message}


def _action(label: str, action_id: str) -> dict:
    return {"action_id": action_id, "label": label, "kind": "form", "fields": []}


def _action_with_note(label: str, action_id: str) -> dict:
    return {
        "action_id": action_id,
        "label": label,
        "kind": "form",
        "fields": [
            {
                "name": "note",
                "kind": "string",
                "label": "Anteckning (valfri)",
            }
        ],
    }


def _handle_action(
    *,
    action_id: str,
    input_data: dict[str, object],
    state: dict[str, object],
    output_dir: Path,
) -> dict:
    step = _safe_int(state.get("step"), 0)
    note = input_data.get("note") if isinstance(input_data.get("note"), str) else ""

    if action_id == "continue":
        step += 1
    elif action_id == "reset":
        step = 0
    elif action_id == "finish":
        pass
    else:
        return {
            "outputs": [_notice("error", f"Okänd action_id: '{action_id}'")],
            "next_actions": [_action("Avsluta", "finish")],
            "state": {"step": step},
        }

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    artifact_name = _write_artifact(
        output_dir=output_dir,
        name=f"step_{step}_{timestamp}.txt",
        content=(f"Demo next_actions\naction_id={action_id}\nstep={step}\nnote={note}\n"),
    )

    outputs = [
        _notice("info", f"Action '{action_id}' kördes. Steg = {step}."),
        {
            "kind": "markdown",
            "markdown": (
                f"**Steg:** {step}\n\n"
                f"**Artifact:** `{artifact_name}`\n\n"
                f"**Anteckning:** {note or '_ingen_'}\n"
            ),
        },
    ]

    if action_id == "finish" or step >= 3:
        next_actions: list[dict] = []
    else:
        next_actions = [
            _action_with_note("Nästa steg", "continue"),
            _action("Nollställ", "reset"),
            _action("Avsluta", "finish"),
        ]

    return {
        "outputs": outputs,
        "next_actions": next_actions,
        "state": {"step": step},
    }


def run_tool(input_dir: str, output_dir: str) -> dict:
    input_root = Path(input_dir)
    out = Path(output_dir)

    action_id, action_input, state = get_action_parts()
    if action_id is not None:
        return _handle_action(
            action_id=action_id,
            input_data=action_input,
            state=state,
            output_dir=out,
        )

    manifest_files = list_input_files()
    primary_file = next(
        iter(manifest_files),
        None,
    )
    if primary_file is not None:
        path = Path(str(primary_file["path"]))
        file_bytes = int(primary_file["bytes"])
        input_files_count = len(manifest_files)
    else:
        primary_path = next(
            (file for file in sorted(input_root.glob("*")) if file.is_file()),
            None,
        )
        if primary_path is None:
            return {
                "outputs": [
                    _notice("error", "Ingen indatafil hittades. Ladda upp minst en fil."),
                ],
                "next_actions": [],
                "state": None,
            }

        path = primary_path
        file_bytes = primary_path.stat().st_size
        input_files_count = len([file for file in input_root.iterdir() if file.is_file()])

    if not manifest_files:
        manifest_files = [
            {"name": file.name, "path": str(file), "bytes": file.stat().st_size}
            for file in sorted(input_root.glob("*"))
            if file.is_file()
        ]

    if not manifest_files:
        return {
            "outputs": [
                _notice("error", "Ingen indatafil hittades. Ladda upp minst en fil."),
            ],
            "next_actions": [],
            "state": None,
        }

    files = [
        {"name": str(item["name"]), "bytes": int(item["bytes"])}
        for item in manifest_files
        if "name" in item and "bytes" in item
    ]

    snippet = ""
    try:
        snippet = path.read_text(encoding="utf-8", errors="replace")[:200]
    except OSError:
        snippet = ""

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    artifact_name = _write_artifact(
        output_dir=out,
        name=f"upload_{timestamp}.txt",
        content=(f"Uploaded file: {path.name}\nbytes: {file_bytes}\nsnippet:\n{snippet}\n"),
    )

    outputs: list[dict] = [
        _notice("info", f"Uppladdad fil: {path.name} ({file_bytes} byte)."),
        {
            "kind": "markdown",
            "markdown": (
                "Det här är ett **demoverktyg** för att testa `next_actions` i SPA.\n\n"
                f"- Artifact: `{artifact_name}`\n"
                f"- Input manifest filer: **{input_files_count}**\n"
                "\n"
                "*Obs: session-state sparas mellan körningar. Använd **Nollställ** "
                "om du vill börja om.*\n"
            ),
        },
    ]

    if files:
        outputs.append(
            {
                "kind": "table",
                "title": "Filer (input manifest)",
                "columns": [
                    {"key": "name", "label": "Namn"},
                    {"key": "bytes", "label": "Byte"},
                ],
                "rows": files,
            }
        )

    return {
        "outputs": outputs,
        "next_actions": [
            _action_with_note("Nästa steg", "continue"),
            _action("Nollställ", "reset"),
            _action("Avsluta", "finish"),
        ],
        "state": {"step": 0},
    }
