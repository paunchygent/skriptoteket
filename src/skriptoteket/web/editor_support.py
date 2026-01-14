from __future__ import annotations

from uuid import UUID

from skriptoteket.domain.catalog.models import Tool
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.scripting.artifacts import ArtifactsManifest
from skriptoteket.domain.scripting.models import ToolRun, ToolVersion, VersionState
from skriptoteket.domain.scripting.policies import (
    can_view_version as _can_view_version,
)
from skriptoteket.domain.scripting.policies import (
    visible_versions_for_actor as _visible_versions_for_actor,
)
from skriptoteket.protocols.catalog import ToolMaintainerRepositoryProtocol

DEFAULT_ENTRYPOINT = "run_tool"
STARTER_TEMPLATE = '''"""
SKRIPTOTEKET STARTMALL
======================
Detta är en mall som visar hur verktyg i Skriptoteket fungerar.
ERSÄTT denna kod med din egen verktygslogik.

Demonstrerar:
- Indatafiler via `list_input_files()` (toolkit)
- Indata via `read_inputs()` (första körningen) och `get_action_parts()`
  (uppföljning via next_actions)
- Användarinställningar via `read_settings()` (toolkit; memory.json)
- Utdatatyper: notice, markdown, table (+ fler i kommentarer)
- Skriva artefakter till output_dir
- next_actions och state
"""
from __future__ import annotations

import csv
from pathlib import Path

from pdf_helper import save_as_pdf
from skriptoteket_toolkit import get_action_parts, list_input_files, read_inputs, read_settings


def run_tool(input_dir: str, output_dir: str) -> dict:
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    # ─── INDATA (första körningen eller uppföljning) ───
    # get_action_parts(): (None, {}, {}) om det inte är en action-körning.
    action_id, action_input, state_in = get_action_parts()

    # Första körningen: read_inputs() (formvärden från input_schema, utan filer).
    # Uppföljning (next_actions): action_input + state_in från get_action_parts().
    inputs = action_input if action_id else read_inputs()
    # Exempel: title = inputs.get("title")

    # ─── INDATAFILER ───
    # Manifest innehåller: name (originalnamn), path (absolut sökväg), bytes (storlek)
    files = list_input_files()

    # ─── ANVÄNDARINSTÄLLNINGAR (valfritt) ───
    # Läs inställningar som användaren sparat via "Inställningar"-panelen
    settings = read_settings()
    # Exempel: threshold = settings.get("threshold", 10)

    # ─── BEARBETA FILER ───
    file_rows = []
    for f in files:
        if not isinstance(f, dict):
            continue
        file_rows.append(
            {
                "name": f.get("name"),
                "path": f.get("path"),
                "bytes": f.get("bytes"),
            }
        )

    threshold = None
    if action_id == "refine":
        try:
            threshold = int(inputs.get("threshold", 0))
        except (TypeError, ValueError):
            threshold = 0
        file_rows = [
            row
            for row in file_rows
            if isinstance(row.get("bytes"), int) and row["bytes"] >= threshold
        ]

        export_format = str(inputs.get("format", "")).strip().lower()
        if export_format == "csv":
            export_path = output_root / "uppladdade_filer.csv"
            with export_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["name", "bytes", "path"])
                writer.writeheader()
                writer.writerows(file_rows)
        elif export_format == "pdf":
            rows_html = "".join(
                f"<tr><td>{row.get('name','')}</td><td>{row.get('bytes','')}</td></tr>"
                for row in file_rows
            )
            html = f"""
            <h1>Uppladdade filer</h1>
            <p>Tröskel: {threshold} byte</p>
            <table border="1" cellspacing="0" cellpadding="6">
              <thead><tr><th>Namn</th><th>Storlek (byte)</th></tr></thead>
              <tbody>{rows_html}</tbody>
            </table>
            """
            save_as_pdf(html, output_dir, "uppladdade_filer.pdf")

    # ─── SKRIV ARTEFAKT (valfritt) ───
    # Filer i output_dir blir nedladdningsbara artefakter
    summary_path = output_root / "sammanfattning.txt"
    summary_path.write_text(
        (
            f"Åtgärd: {action_id}\\n"
            f"Antal filer: {len(files)}\\n"
            f"Indata: {inputs}\\n"
            f"Inställningar: {settings}"
        )
    )

    # ─── STATE (valfritt) ───
    # state sparas mellan körningar och skickas tillbaka vid nästa run
    # (t.ex. uppföljning via next_actions)
    state = state_in or {}
    runs = state.get("runs")
    state["runs"] = runs + 1 if isinstance(runs, int) else 1

    # ─── RETURNERA RESULTAT ───
    outputs = [
        # notice: Snabbmeddelanden (info/warning/error)
        {
            "kind": "notice",
            "level": "info",
            "message": (
                f"{len(files)} fil(er) mottagna."
                if threshold is None
                else f"{len(file_rows)} fil(er) matchade tröskel ≥ {threshold}."
            ),
        },
        # markdown: Formaterad text
        {
            "kind": "markdown",
            "markdown": (
                "## Resultat\\n\\n"
                "Ersätt denna mall med din egen logik.\\n\\n"
                f"**Körningar i denna session:** {state['runs']}\\n"
            ),
        },
        # table: Strukturerad data
        {
            "kind": "table",
            "title": "Uppladdade filer",
            "columns": [
                {"key": "name", "label": "Namn"},
                {"key": "bytes", "label": "Storlek (byte)"},
            ],
            "rows": file_rows,
        },
    ]

    # ─── AVANCERAT: FLER UTDATATYPER (avkommentera vid behov) ───
    # json: Visa rådata
    # outputs.append({"kind": "json", "title": "Debug-data", "value": {"files": files}})
    #
    # html_sandboxed: Rendera HTML i iframe (för specialfall)
    # outputs.append({"kind": "html_sandboxed", "html": "<p>Custom HTML</p>"})

    # ─── AVANCERAT: UPPFÖLJNINGSFORMULÄR (avkommentera vid behov) ───
    # next_actions låter användaren skicka in ytterligare data efter första körningen
    next_actions = [
        {
            "action_id": "refine",
            "label": "Förfina resultat",
            "kind": "form",
            "fields": [
                {"name": "threshold", "label": "Tröskel (byte)", "kind": "integer"},
                {
                    "name": "format",
                    "label": "Exportformat",
                    "kind": "enum",
                    "options": [
                        {"value": "pdf", "label": "PDF"},
                        {"value": "csv", "label": "CSV"},
                    ],
                },
            ],
        }
    ]

    return {"outputs": outputs, "next_actions": next_actions, "state": state}
'''


async def require_tool_access(
    *,
    actor: User,
    tool_id: UUID,
    maintainers: ToolMaintainerRepositoryProtocol,
) -> bool:
    if actor.role in {Role.ADMIN, Role.SUPERUSER}:
        return True

    is_tool_maintainer = await maintainers.is_maintainer(tool_id=tool_id, user_id=actor.id)
    if not is_tool_maintainer:
        raise DomainError(
            code=ErrorCode.FORBIDDEN,
            message="Insufficient permissions",
            details={"tool_id": str(tool_id)},
        )
    return is_tool_maintainer


def visible_versions_for_actor(
    *,
    actor: User,
    versions: list[ToolVersion],
    is_tool_maintainer: bool,
) -> list[ToolVersion]:
    return _visible_versions_for_actor(
        actor=actor,
        versions=versions,
        is_tool_maintainer=is_tool_maintainer,
    )


def select_default_version(
    *,
    actor: User,
    tool: Tool,
    versions: list[ToolVersion],
    is_tool_maintainer: bool,
) -> ToolVersion | None:
    visible_versions = visible_versions_for_actor(
        actor=actor,
        versions=versions,
        is_tool_maintainer=is_tool_maintainer,
    )

    if actor.role in {Role.ADMIN, Role.SUPERUSER}:
        for version in visible_versions:
            if version.state is VersionState.IN_REVIEW:
                return version

    # Prefer latest visible draft, then active, then latest visible.
    for version in visible_versions:
        if version.state is VersionState.DRAFT:
            return version

    if tool.active_version_id is not None:
        for version in visible_versions:
            if version.id == tool.active_version_id:
                return version

    return visible_versions[0] if visible_versions else None


def artifacts_for_run(run: ToolRun) -> list[dict[str, object]]:
    manifest = ArtifactsManifest.model_validate(run.artifacts_manifest)
    return [
        {
            "artifact_id": artifact.artifact_id,
            "path": artifact.path,
            "bytes": artifact.bytes,
            "download_url": f"/admin/tool-runs/{run.id}/artifacts/{artifact.artifact_id}",
        }
        for artifact in manifest.artifacts
    ]


def is_allowed_to_view_version(
    *,
    actor: User,
    version: ToolVersion,
    is_tool_maintainer: bool,
) -> bool:
    return _can_view_version(actor=actor, version=version, is_tool_maintainer=is_tool_maintainer)
