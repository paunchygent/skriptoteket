"""User-facing tool execution routes.

Routes for authenticated users to run published tools and view results.
"""

from uuid import UUID

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import HTMLResponse, Response

from skriptoteket.application.scripting.commands import RunActiveToolCommand
from skriptoteket.application.scripting.interactive_tools import (
    GetSessionStateQuery,
    StartActionCommand,
)
from skriptoteket.domain.errors import DomainError, not_found, validation_error
from skriptoteket.domain.identity.models import Session, User
from skriptoteket.domain.scripting.artifacts import ArtifactsManifest
from skriptoteket.domain.scripting.models import RunContext, RunStatus, ToolRun
from skriptoteket.protocols.catalog import ToolRepositoryProtocol
from skriptoteket.protocols.interactive_tools import (
    GetSessionStateHandlerProtocol,
    StartActionHandlerProtocol,
)
from skriptoteket.protocols.scripting import (
    RunActiveToolHandlerProtocol,
    ToolRunRepositoryProtocol,
    ToolVersionRepositoryProtocol,
)
from skriptoteket.web.auth.dependencies import get_current_session, require_user
from skriptoteket.web.interactive_action_forms import parse_action_input
from skriptoteket.web.pages.admin_scripting_support import (
    is_hx_request,
    parse_uuid,
    status_code_for_error,
)
from skriptoteket.web.templating import templates
from skriptoteket.web.ui_text import ui_error_message

router = APIRouter(prefix="/tools")


def _run_succeeded(status: RunStatus | str) -> bool:
    key = status.value if isinstance(status, RunStatus) else str(status)
    return key == RunStatus.SUCCEEDED.value


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


async def _load_production_run_for_user(
    *,
    runs: ToolRunRepositoryProtocol,
    run_id: UUID,
    user: User,
) -> ToolRun:
    run = await runs.get_by_id(run_id=run_id)
    if run is None or run.requested_by_user_id != user.id:
        raise not_found("ToolRun", str(run_id))
    if run.context is not RunContext.PRODUCTION:
        raise not_found("ToolRun", str(run_id))
    return run


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
    sessions: FromDishka[GetSessionStateHandlerProtocol],
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
            error = ui_error_message(exc)
            return templates.TemplateResponse(
                request=request,
                name="tools/partials/run_error_with_toast.html",
                context={
                    "request": request,
                    "error": error,
                    "message": "Körning misslyckades.",
                    "type": "error",
                },
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
    interactive_context = "default"
    interactive_state_rev: int | None = None
    if run.ui_payload is not None and run.ui_payload.next_actions:
        try:
            session_state = (
                await sessions.handle(
                    actor=user,
                    query=GetSessionStateQuery(tool_id=run.tool_id, context=interactive_context),
                )
            ).session_state
            interactive_state_rev = session_state.state_rev
        except DomainError:
            interactive_state_rev = None

    if hx_request:
        succeeded = _run_succeeded(run.status)
        return templates.TemplateResponse(
            request=request,
            name="tools/partials/run_result_with_toast.html",
            context={
                "request": request,
                "run": run,
                "artifacts": _user_artifacts_for_run(run),
                "interactive_context": interactive_context,
                "interactive_state_rev": interactive_state_rev,
                "message": "Körning lyckades." if succeeded else "Körning misslyckades.",
                "type": "success" if succeeded else "error",
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
            "interactive_context": interactive_context,
            "interactive_state_rev": interactive_state_rev,
        },
    )


@router.post("/interactive/start_action", response_class=HTMLResponse)
@inject
async def start_interactive_action(
    request: Request,
    handler: FromDishka[StartActionHandlerProtocol],
    runs: FromDishka[ToolRunRepositoryProtocol],
    user: User = Depends(require_user),
    session: Session | None = Depends(get_current_session),
) -> Response:
    csrf_token = session.csrf_token if session else ""
    hx_request = is_hx_request(request)

    action_error: str | None = None
    interactive_context = "default"
    interactive_state_rev: int | None = None

    run: ToolRun | None = None
    try:
        form = await request.form()
        run_id_raw = form.get("_run_id")
        run_id = parse_uuid(run_id_raw if isinstance(run_id_raw, str) else None)
        if run_id is None:
            raise validation_error("run_id is required")

        action_id_raw = form.get("_action_id")
        if not isinstance(action_id_raw, str) or not action_id_raw.strip():
            raise validation_error("action_id is required")
        action_id = action_id_raw.strip()

        context_raw = form.get("_context")
        if isinstance(context_raw, str) and context_raw.strip():
            interactive_context = context_raw.strip()

        expected_state_rev_raw = form.get("_expected_state_rev")
        if not isinstance(expected_state_rev_raw, str) or expected_state_rev_raw.strip() == "":
            raise validation_error("expected_state_rev is required")
        try:
            interactive_state_rev = int(expected_state_rev_raw)
        except ValueError as exc:
            raise validation_error(
                "expected_state_rev must be an integer",
                details={"expected_state_rev": expected_state_rev_raw},
            ) from exc

        run = await _load_production_run_for_user(runs=runs, run_id=run_id, user=user)

        if run.ui_payload is None:
            raise validation_error("Run has no ui_payload", details={"run_id": str(run.id)})

        action = next(
            (
                candidate
                for candidate in run.ui_payload.next_actions
                if candidate.action_id == action_id
            ),
            None,
        )
        if action is None:
            raise validation_error(
                "Action not found on run",
                details={"run_id": str(run.id), "action_id": action_id},
            )

        parsed_input = parse_action_input(action=action, form=form)
        result = await handler.handle(
            actor=user,
            command=StartActionCommand(
                tool_id=run.tool_id,
                context=interactive_context,
                action_id=action_id,
                input=parsed_input,
                expected_state_rev=interactive_state_rev,
            ),
        )

        interactive_state_rev = result.state_rev
        run = await _load_production_run_for_user(runs=runs, run_id=result.run_id, user=user)
    except DomainError as exc:
        action_error = ui_error_message(exc)
        status_code = status_code_for_error(exc)

        if hx_request:
            if run is None:
                return templates.TemplateResponse(
                    request=request,
                    name="tools/partials/run_error_with_toast.html",
                    context={
                        "request": request,
                        "error": action_error,
                        "message": "Åtgärden misslyckades.",
                        "type": "error",
                    },
                    status_code=status_code,
                )

            return templates.TemplateResponse(
                request=request,
                name="tools/partials/run_result_with_toast.html",
                context={
                    "request": request,
                    "run": run,
                    "artifacts": _user_artifacts_for_run(run),
                    "interactive_context": interactive_context,
                    "interactive_state_rev": interactive_state_rev,
                    "action_error": action_error,
                    "message": "Åtgärden misslyckades.",
                    "type": "error",
                },
                status_code=status_code,
            )

        if run is None:
            return templates.TemplateResponse(
                request=request,
                name="error.html",
                context={
                    "request": request,
                    "user": user,
                    "csrf_token": csrf_token,
                    "error_code": str(status_code),
                    "message": action_error,
                },
                status_code=status_code,
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
                "interactive_context": interactive_context,
                "interactive_state_rev": interactive_state_rev,
                "action_error": action_error,
            },
            status_code=status_code,
        )

    if hx_request:
        succeeded = _run_succeeded(run.status) if run is not None else False
        return templates.TemplateResponse(
            request=request,
            name="tools/partials/run_result_with_toast.html",
            context={
                "request": request,
                "run": run,
                "artifacts": [] if run is None else _user_artifacts_for_run(run),
                "interactive_context": interactive_context,
                "interactive_state_rev": interactive_state_rev,
                "message": "Åtgärden kördes." if succeeded else "Åtgärden kördes (med fel).",
                "type": "success" if succeeded else "error",
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
            "artifacts": [] if run is None else _user_artifacts_for_run(run),
            "interactive_context": interactive_context,
            "interactive_state_rev": interactive_state_rev,
            "action_error": action_error,
        },
    )
