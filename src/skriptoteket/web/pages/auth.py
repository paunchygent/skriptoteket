from uuid import UUID

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from skriptoteket.application.identity.commands import LoginCommand, LogoutCommand
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.protocols.identity import LoginHandlerProtocol, LogoutHandlerProtocol
from skriptoteket.web.auth.dependencies import get_session_id
from skriptoteket.web.templating import templates

router = APIRouter()


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str | None = None) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"error": error, "user": None, "csrf_token": ""},
    )


@router.post("/login")
@inject
async def login(
    request: Request,
    settings: FromDishka[Settings],
    handler: FromDishka[LoginHandlerProtocol],
    email: str = Form(...),
    password: str = Form(...),
) -> Response:
    try:
        result = await handler.handle(LoginCommand(email=email, password=password))
    except DomainError as exc:
        if exc.code in {ErrorCode.INVALID_CREDENTIALS, ErrorCode.UNAUTHORIZED}:
            return templates.TemplateResponse(
                request=request,
                name="login.html",
                context={
                    "error": "Fel e-post eller lösenord.",
                    "user": None,
                    "csrf_token": "",
                },
            )
        raise

    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=str(result.session_id),
        max_age=settings.SESSION_TTL_SECONDS,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path="/",
    )
    return response


@router.post("/logout")
@inject
async def logout(
    request: Request,
    settings: FromDishka[Settings],
    handler: FromDishka[LogoutHandlerProtocol],
    csrf_token: str = Form(...),
    session_id: UUID | None = Depends(get_session_id),
) -> RedirectResponse:
    if session_id is None:
        return RedirectResponse(url="/login", status_code=303)

    await handler.handle(LogoutCommand(session_id=session_id, csrf_token=csrf_token))
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(key=settings.SESSION_COOKIE_NAME, path="/")
    return response
