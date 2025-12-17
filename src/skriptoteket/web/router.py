from fastapi import APIRouter, Depends

from skriptoteket.web.auth.dependencies import require_user
from skriptoteket.web.pages import admin_scripting as admin_scripting_pages
from skriptoteket.web.pages import admin_tools as admin_tools_pages
from skriptoteket.web.pages import auth as auth_pages
from skriptoteket.web.pages import browse as browse_pages
from skriptoteket.web.pages import home as home_pages
from skriptoteket.web.pages import my_runs as my_runs_pages
from skriptoteket.web.pages import my_tools as my_tools_pages
from skriptoteket.web.pages import suggestions as suggestions_pages
from skriptoteket.web.pages import tools as tools_pages

router = APIRouter()
router.include_router(auth_pages.router)

protected = APIRouter(dependencies=[Depends(require_user)])
protected.include_router(home_pages.router)
protected.include_router(browse_pages.router)
protected.include_router(tools_pages.router)
protected.include_router(my_runs_pages.router)
protected.include_router(my_tools_pages.router)
protected.include_router(suggestions_pages.router)
protected.include_router(admin_tools_pages.router)
protected.include_router(admin_scripting_pages.router)
router.include_router(protected)
