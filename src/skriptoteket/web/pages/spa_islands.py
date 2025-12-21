from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from skriptoteket.domain.identity.models import Session, User
from skriptoteket.web.auth.dependencies import get_current_session, require_user
from skriptoteket.web.templating import templates

router = APIRouter(prefix="/spa")


@router.get("/demo", response_class=HTMLResponse)
async def spa_demo(
    request: Request,
    user: User = Depends(require_user),
    session: Session | None = Depends(get_current_session),
) -> HTMLResponse:
    csrf_token = session.csrf_token if session else ""
    return templates.TemplateResponse(
        request=request,
        name="spa/demo.html",
        context={
            "request": request,
            "title": "SPA island demo",
            "user": user,
            "csrf_token": csrf_token,
        },
    )
