from uuid import UUID

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from skriptoteket.application.scripting.interactive_tools import (
    GetSessionStateQuery,
    StartActionCommand,
)
from skriptoteket.domain.errors import DomainError, not_found
from skriptoteket.domain.identity.models import Session, User
from skriptoteket.domain.identity.role_guards import require_at_least_role
from skriptoteket.domain.scripting.artifacts import ArtifactsManifest
from skriptoteket.domain.scripting.models import RunContext, RunStatus, ToolRun
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.interactive_tools import (
    GetSessionStateHandlerProtocol,
    StartActionHandlerProtocol,
)
from skriptoteket.protocols.scripting import ToolRunRepositoryProtocol
from skriptoteket.web.auth.dependencies import get_current_session, require_user
from skriptoteket.web.pages.admin_scripting_support import is_hx_request, status_code_for_error
from skriptoteket.web.templating import templates
from skriptoteket.web.ui_text import ui_error_message

router = APIRouter(prefix="/apps")


def _run_succeeded(status: RunStatus | str) -> bool:
    key = status.value if isinstance(status, RunStatus) else str(status)
    return key == RunStatus.SUCCEEDED.value


def _user_artifacts_for_run(run: ToolRun) -> list[dict[str, object]]:
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


@router.get("/{app_id}", response_class=HTMLResponse)
@inject
async def view_app(
    request: Request,
    app_id: str,
    registry: FromDishka[CuratedAppRegistryProtocol],
    runs: FromDishka[ToolRunRepositoryProtocol],
    sessions: FromDishka[GetSessionStateHandlerProtocol],
    user: User = Depends(require_user),
    session: Session | None = Depends(get_current_session),
) -> HTMLResponse:
    csrf_token = session.csrf_token if session else ""

    app = registry.get_by_app_id(app_id=app_id)
    if app is None:
        raise not_found("CuratedApp", app_id)
    require_at_least_role(user=user, role=app.min_role)

    latest_run = await runs.get_latest_for_user_and_tool(
        user_id=user.id,
        tool_id=app.tool_id,
        context=RunContext.PRODUCTION,
    )

    interactive_context = "default"
    interactive_state_rev: int | None = None
    if (
        latest_run is not None
        and latest_run.ui_payload is not None
        and latest_run.ui_payload.next_actions
    ):
        try:
            session_state = (
                await sessions.handle(
                    actor=user,
                    query=GetSessionStateQuery(
                        tool_id=app.tool_id,
                        context=interactive_context,
                    ),
                )
            ).session_state
            interactive_state_rev = session_state.state_rev
        except DomainError:
            interactive_state_rev = None

    return templates.TemplateResponse(
        request=request,
        name="apps/detail.html",
        context={
            "request": request,
            "user": user,
            "csrf_token": csrf_token,
            "app": app,
            "run": latest_run,
            "artifacts": [] if latest_run is None else _user_artifacts_for_run(latest_run),
            "interactive_context": interactive_context,
            "interactive_state_rev": interactive_state_rev,
        },
    )


@router.post("/{app_id}/start", response_class=HTMLResponse)
@inject
async def start_app(
    request: Request,
    app_id: str,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[StartActionHandlerProtocol],
    runs: FromDishka[ToolRunRepositoryProtocol],
    sessions: FromDishka[GetSessionStateHandlerProtocol],
    user: User = Depends(require_user),
    session: Session | None = Depends(get_current_session),
) -> Response:
    csrf_token = session.csrf_token if session else ""
    hx_request = is_hx_request(request)

    app = registry.get_by_app_id(app_id=app_id)
    if app is None:
        raise not_found("CuratedApp", app_id)
    require_at_least_role(user=user, role=app.min_role)

    interactive_context = "default"

    try:
        session_state = (
            await sessions.handle(
                actor=user,
                query=GetSessionStateQuery(tool_id=app.tool_id, context=interactive_context),
            )
        ).session_state

        result = await handler.handle(
            actor=user,
            command=StartActionCommand(
                tool_id=app.tool_id,
                context=interactive_context,
                action_id="start",
                input={},
                expected_state_rev=session_state.state_rev,
            ),
        )

        run = await _load_production_run_for_user(runs=runs, run_id=result.run_id, user=user)
    except DomainError as exc:
        if hx_request:
            action_error = ui_error_message(exc)
            return templates.TemplateResponse(
                request=request,
                name="tools/partials/run_error_with_toast.html",
                context={
                    "request": request,
                    "error": action_error,
                    "message": "Start misslyckades.",
                    "type": "error",
                },
                status_code=status_code_for_error(exc),
            )

        action_error = ui_error_message(exc)
        status_code = status_code_for_error(exc)
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
                "interactive_state_rev": result.state_rev,
                "message": "Appen startade." if succeeded else "Appen startade (med fel).",
                "type": "success" if succeeded else "error",
            },
        )

    return RedirectResponse(url=f"/apps/{app.app_id}", status_code=303)
