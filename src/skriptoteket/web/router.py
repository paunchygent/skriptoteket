from fastapi import APIRouter, Depends

from skriptoteket.web.auth.dependencies import require_user
from skriptoteket.web.pages import admin_tools as admin_tools_pages
from skriptoteket.web.pages import auth as auth_pages
from skriptoteket.web.pages import browse as browse_pages
from skriptoteket.web.pages import home as home_pages
from skriptoteket.web.pages import suggestions as suggestions_pages

router = APIRouter()
router.include_router(auth_pages.router)

protected = APIRouter(dependencies=[Depends(require_user)])
protected.include_router(home_pages.router)
protected.include_router(browse_pages.router)
protected.include_router(suggestions_pages.router)
protected.include_router(admin_tools_pages.router)
router.include_router(protected)
