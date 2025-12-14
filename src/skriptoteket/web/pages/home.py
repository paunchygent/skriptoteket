from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from skriptoteket.domain.identity.models import Session, User
from skriptoteket.web.auth.dependencies import get_current_session, require_user
from skriptoteket.web.templating import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def home(
    request: Request,
    user: User = Depends(require_user),
    session: Session | None = Depends(get_current_session),
) -> HTMLResponse:
    csrf_token = session.csrf_token if session else ""
    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={"user": user, "csrf_token": csrf_token},
    )
