from uuid import UUID

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from skriptoteket.application.identity.commands import LogoutCommand
from skriptoteket.config import Settings
from skriptoteket.protocols.identity import LogoutHandlerProtocol
from skriptoteket.web.auth.dependencies import get_session_id

router = APIRouter()


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
