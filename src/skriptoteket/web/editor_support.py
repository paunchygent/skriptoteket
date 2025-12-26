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
Detta är en pedagogisk mall som visar hur Skriptoteket-kontrakt fungerar.
ERSÄTT denna kod med din egen verktygslogik.

Demonstrerar:
- Indatafiler via SKRIPTOTEKET_INPUT_MANIFEST
- Indata via SKRIPTOTEKET_INPUTS (input_schema)
- Användarinställningar via SKRIPTOTEKET_MEMORY_PATH
- Utdatatyper: notice, markdown, table (+ fler i kommentarer)
- Skriva artefakter till output_dir
- next_actions och state (kommenterade exempel)
"""
from __future__ import annotations

import json
import os
from pathlib import Path


def run_tool(input_dir: str, output_dir: str) -> dict:
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    # ─── INDATA (valfritt) ───
    # Form-baserade indata skickas via SKRIPTOTEKET_INPUTS (JSON-objekt).
    inputs_raw = os.environ.get("SKRIPTOTEKET_INPUTS", "")
    inputs = json.loads(inputs_raw) if inputs_raw.strip() else {}
    # Exempel: title = inputs.get("title")

    # ─── INDATAFILER ───
    # Manifest innehåller: name (originalnamn), path (absolut sökväg), bytes (storlek)
    manifest_raw = os.environ.get("SKRIPTOTEKET_INPUT_MANIFEST", "")
    manifest = json.loads(manifest_raw) if manifest_raw.strip() else {"files": []}
    files = manifest.get("files", []) if isinstance(manifest, dict) else []

    # ─── ANVÄNDARINSTÄLLNINGAR (valfritt) ───
    # Läs inställningar som användaren sparat via "Inställningar"-panelen
    settings: dict = {}
    memory_path = os.environ.get("SKRIPTOTEKET_MEMORY_PATH")
    if memory_path and Path(memory_path).exists():
        memory = json.loads(Path(memory_path).read_text())
        settings = memory.get("settings", {})
    # Exempel: threshold = settings.get("threshold", 10)

    # ─── BEARBETA FILER ───
    file_rows = []
    for f in files:
        file_rows.append({"name": f["name"], "path": f["path"], "bytes": f["bytes"]})

    # ─── SKRIV ARTEFAKT (valfritt) ───
    # Filer i output_dir blir nedladdningsbara artefakter
    summary_path = output_root / "sammanfattning.txt"
    summary_path.write_text(
        f"Antal filer: {len(files)}\\nIndata: {inputs}\\nInställningar: {settings}"
    )

    # ─── RETURNERA RESULTAT ───
    outputs = [
        # notice: Snabbmeddelanden (info/warning/error)
        {"kind": "notice", "level": "info", "message": f"{len(files)} fil(er) mottagna."},
        # markdown: Formaterad text
        {"kind": "markdown", "markdown": "## Resultat\\n\\nErsätt denna mall med din egen logik."},
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
    #
    # vega_lite: Diagram/visualiseringar (kräver Vega-Lite-spec)
    # outputs.append({"kind": "vega_lite", "spec": {"$schema": "...", "data": {...}}})

    # ─── AVANCERAT: UPPFÖLJNINGSFORMULÄR (avkommentera vid behov) ───
    # next_actions låter användaren skicka in ytterligare data efter första körningen
    next_actions = []
    # next_actions = [{
    #     "action_id": "refine",
    #     "label": "Förfina resultat",
    #     "kind": "form",
    #     "fields": [
    #         {"name": "threshold", "label": "Tröskel", "kind": "integer"},
    #         {"name": "format", "label": "Format", "kind": "enum", "options": [
    #             {"value": "pdf", "label": "PDF"},
    #             {"value": "csv", "label": "CSV"},
    #         ]},
    #     ],
    # }]

    # ─── AVANCERAT: STATE FÖR FLERSTEGSFLÖDEN (avkommentera vid behov) ───
    # state sparas mellan körningar och skickas tillbaka vid nästa run
    state = None
    # state = {"step": 1, "previous_results": [...]}

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
