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
STARTER_TEMPLATE = """from __future__ import annotations

import json
import os
from pathlib import Path


def run_tool(input_dir: str, output_dir: str) -> dict:
    input_root = Path(input_dir)
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    manifest_raw = os.environ.get("SKRIPTOTEKET_INPUT_MANIFEST", "")
    manifest = json.loads(manifest_raw) if manifest_raw.strip() else {"files": []}
    files = manifest.get("files", []) if isinstance(manifest, dict) else []

    if not files:
        return {
            "outputs": [
                {"kind": "notice", "level": "error", "message": "Ingen indatafil hittades."}
            ],
            "next_actions": [],
            "state": None,
        }

    first = Path(str(files[0].get("path", "")))
    size = first.stat().st_size if first.exists() else 0

    return {
        "outputs": [
            {
                "kind": "notice",
                "level": "info",
                "message": f"Uppladdad fil: {first.name} ({size} byte).",
            }
        ],
        "next_actions": [],
        "state": None,
    }
"""


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
