from uuid import UUID

from fastapi import Request
from fastapi.responses import RedirectResponse, Response

from skriptoteket.domain.catalog.models import Tool
from skriptoteket.domain.errors import DomainError, ErrorCode, not_found
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.execution import ArtifactsManifest
from skriptoteket.domain.scripting.policies import (
    can_view_version as _can_view_version,
    visible_versions_for_actor as _visible_versions_for_actor,
)
from skriptoteket.domain.scripting.models import ToolRun, ToolVersion, VersionState
from skriptoteket.protocols.catalog import ToolRepositoryProtocol
from skriptoteket.protocols.scripting import ToolVersionRepositoryProtocol
from skriptoteket.web.templating import templates


def status_code_for_error(exc: DomainError) -> int:
    if exc.code is ErrorCode.NOT_FOUND:
        return 404
    if exc.code is ErrorCode.FORBIDDEN:
        return 403
    if exc.code is ErrorCode.CONFLICT:
        return 409
    if exc.code is ErrorCode.VALIDATION_ERROR:
        return 400
    if exc.code is ErrorCode.SERVICE_UNAVAILABLE:
        return 503
    return 500


def is_hx_request(request: Request) -> bool:
    return request.headers.get("HX-Request") == "true"


def redirect_with_hx(*, request: Request, url: str) -> RedirectResponse:
    response = RedirectResponse(url=url, status_code=303)
    if is_hx_request(request):
        response.headers["HX-Redirect"] = url
    return response


def parse_uuid(value: str | None) -> UUID | None:
    if not value:
        return None
    try:
        return UUID(value)
    except ValueError:
        return None


def visible_versions_for_actor(*, actor: User, versions: list[ToolVersion]) -> list[ToolVersion]:
    return _visible_versions_for_actor(actor=actor, versions=versions)


def select_default_version(
    *, actor: User, tool: Tool, versions: list[ToolVersion]
) -> ToolVersion | None:
    visible_versions = visible_versions_for_actor(actor=actor, versions=versions)

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
    versions: list[ToolVersion],
) -> bool:
    return _can_view_version(actor=actor, version=version, versions=versions)


def editor_context(
    *,
    request: Request,
    user: User,
    csrf_token: str,
    tool: Tool,
    versions: list[ToolVersion],
    selected_version: ToolVersion | None,
    editor_entrypoint: str,
    editor_source_code: str,
    run: ToolRun | None,
    error: str | None,
) -> dict[str, object]:
    visible_versions = visible_versions_for_actor(actor=user, versions=versions)

    draft_version = (
        selected_version
        if selected_version is not None and selected_version.state is VersionState.DRAFT
        else None
    )
    save_action = f"/admin/tools/{tool.id}/versions"
    if draft_version is not None:
        save_action = f"/admin/tool-versions/{draft_version.id}/save"

    is_draft = draft_version is not None
    derived_from_version_id = (
        selected_version.id if (selected_version is not None and not is_draft) else None
    )

    return {
        "request": request,
        "user": user,
        "csrf_token": csrf_token,
        "tool": tool,
        "versions": visible_versions,
        "selected_version": selected_version,
        "editor_entrypoint": editor_entrypoint,
        "editor_source_code": editor_source_code,
        "save_action": save_action,
        "save_mode": "snapshot" if is_draft else "create_draft",
        "derived_from_version_id": derived_from_version_id,
        "run": run,
        "artifacts": artifacts_for_run(run) if run else [],
        "error": error,
    }


async def render_editor_for_tool_id(
    *,
    request: Request,
    user: User,
    csrf_token: str,
    tools: ToolRepositoryProtocol,
    versions_repo: ToolVersionRepositoryProtocol,
    tool_id: UUID,
    editor_entrypoint: str,
    editor_source_code: str,
    run: ToolRun | None,
    error: str | None,
    status_code: int | None = None,
) -> Response:
    tool = await tools.get_by_id(tool_id=tool_id)
    if tool is None:
        raise not_found("Tool", str(tool_id))

    versions = await versions_repo.list_for_tool(tool_id=tool.id, limit=50)
    selected_version = select_default_version(actor=user, tool=tool, versions=versions)
    context = editor_context(
        request=request,
        user=user,
        csrf_token=csrf_token,
        tool=tool,
        versions=versions,
        selected_version=selected_version,
        editor_entrypoint=editor_entrypoint,
        editor_source_code=editor_source_code,
        run=run,
        error=error,
    )
    if status_code is None:
        return templates.TemplateResponse(
            request=request,
            name="admin/script_editor.html",
            context=context,
        )

    return templates.TemplateResponse(
        request=request,
        name="admin/script_editor.html",
        context=context,
        status_code=status_code,
    )


async def render_editor_for_version_id(
    *,
    request: Request,
    user: User,
    csrf_token: str,
    tools: ToolRepositoryProtocol,
    versions_repo: ToolVersionRepositoryProtocol,
    version_id: UUID,
    editor_entrypoint: str | None,
    editor_source_code: str | None,
    run: ToolRun | None,
    error: str | None,
    status_code: int | None = None,
) -> Response:
    version = await versions_repo.get_by_id(version_id=version_id)
    if version is None:
        raise not_found("ToolVersion", str(version_id))

    tool = await tools.get_by_id(tool_id=version.tool_id)
    if tool is None:
        raise not_found("Tool", str(version.tool_id))

    versions = await versions_repo.list_for_tool(tool_id=tool.id, limit=50)
    resolved_entrypoint = editor_entrypoint if editor_entrypoint is not None else version.entrypoint
    resolved_source_code = (
        editor_source_code if editor_source_code is not None else version.source_code
    )
    context = editor_context(
        request=request,
        user=user,
        csrf_token=csrf_token,
        tool=tool,
        versions=versions,
        selected_version=version,
        editor_entrypoint=resolved_entrypoint,
        editor_source_code=resolved_source_code,
        run=run,
        error=error,
    )
    if status_code is None:
        return templates.TemplateResponse(
            request=request,
            name="admin/script_editor.html",
            context=context,
        )

    return templates.TemplateResponse(
        request=request,
        name="admin/script_editor.html",
        context=context,
        status_code=status_code,
    )
