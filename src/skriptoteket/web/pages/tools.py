"""User-facing tool execution routes.

Routes for authenticated users to run published tools and view results.
"""

from uuid import UUID

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import HTMLResponse, Response

from skriptoteket.application.scripting.commands import RunActiveToolCommand
from skriptoteket.domain.errors import DomainError, not_found
from skriptoteket.domain.identity.models import Session, User
from skriptoteket.domain.scripting.execution import ArtifactsManifest
from skriptoteket.domain.scripting.models import ToolRun
from skriptoteket.protocols.catalog import ToolRepositoryProtocol
from skriptoteket.protocols.scripting import (
    RunActiveToolHandlerProtocol,
    ToolVersionRepositoryProtocol,
)
from skriptoteket.web.auth.dependencies import get_current_session, require_user
from skriptoteket.web.pages.admin_scripting_support import (
    is_hx_request,
    status_code_for_error,
)
from skriptoteket.web.templating import templates
from skriptoteket.web.ui_text import ui_error_message

router = APIRouter(prefix="/tools")


def _user_artifacts_for_run(run: ToolRun) -> list[dict[str, object]]:
    """Generate artifact list with user-facing download URLs."""
    manifest = ArtifactsManifest.model_validate(run.artifacts_manifest)
    return [
        {
            "artifact_id": artifact.artifact_id,
            "path": artifact.path,
            "bytes": artifact.bytes,
            "download_url": f"/my-runs/{run.id}/artifacts/{artifact.artifact_id}",
        }
        for artifact in manifest.artifacts
    ]


async def _load_runnable_tool(
    *,
    tools: ToolRepositoryProtocol,
    slug: str,
) -> tuple[object, UUID]:
    """Load a tool that is published and has an active version.

    Returns (tool, active_version_id) or raises not_found.
    """
    tool = await tools.get_by_slug(slug=slug)
    if tool is None:
        raise not_found("Tool", slug)
    if not tool.is_published:
        raise not_found("Tool", slug)
    if tool.active_version_id is None:
        raise not_found("Tool", slug)
    return tool, tool.active_version_id


@router.get("/{slug}/run", response_class=HTMLResponse)
@inject
async def show_run_form(
    request: Request,
    slug: str,
    tools: FromDishka[ToolRepositoryProtocol],
    versions: FromDishka[ToolVersionRepositoryProtocol],
    user: User = Depends(require_user),
    session: Session | None = Depends(get_current_session),
) -> HTMLResponse:
    """Show the run form for a published tool."""
    csrf_token = session.csrf_token if session else ""

    tool, active_version_id = await _load_runnable_tool(tools=tools, slug=slug)

    version = await versions.get_by_id(version_id=active_version_id)
    if version is None:
        raise not_found("Tool", slug)

    return templates.TemplateResponse(
        request=request,
        name="tools/run.html",
        context={
            "request": request,
            "user": user,
            "csrf_token": csrf_token,
            "tool": tool,
            "version": version,
        },
    )


@router.post("/{slug}/run", response_class=HTMLResponse)
@inject
async def execute_tool(
    request: Request,
    slug: str,
    handler: FromDishka[RunActiveToolHandlerProtocol],
    tools: FromDishka[ToolRepositoryProtocol],
    user: User = Depends(require_user),
    session: Session | None = Depends(get_current_session),
    file: UploadFile = File(...),
) -> Response:
    """Execute a published tool and return results."""
    csrf_token = session.csrf_token if session else ""
    hx_request = is_hx_request(request)

    try:
        input_bytes = await file.read()
        result = await handler.handle(
            actor=user,
            command=RunActiveToolCommand(
                tool_slug=slug,
                input_filename=file.filename or "input.bin",
                input_bytes=input_bytes,
            ),
        )
        run = result.run
    except DomainError as exc:
        if hx_request:
            return HTMLResponse(
                f'<div class="huleedu-alert huleedu-alert-error">{ui_error_message(exc)}</div>',
                status_code=status_code_for_error(exc),
            )
        # Re-render form with error
        try:
            tool, _ = await _load_runnable_tool(tools=tools, slug=slug)
        except DomainError:
            raise exc from None
        return templates.TemplateResponse(
            request=request,
            name="tools/run.html",
            context={
                "request": request,
                "user": user,
                "csrf_token": csrf_token,
                "tool": tool,
                "version": None,
                "error": ui_error_message(exc),
            },
            status_code=status_code_for_error(exc),
        )

    # Success - render result
    if hx_request:
        return templates.TemplateResponse(
            request=request,
            name="tools/partials/run_result.html",
            context={
                "request": request,
                "run": run,
                "artifacts": _user_artifacts_for_run(run),
            },
        )

    return templates.TemplateResponse(
        request=request,
        name="tools/result.html",
        context={
            "request": request,
            "user": user,
            "csrf_token": csrf_token,
            "run": run,
            "artifacts": _user_artifacts_for_run(run),
        },
    )
