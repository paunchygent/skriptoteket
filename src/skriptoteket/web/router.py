from fastapi import APIRouter, Depends

from skriptoteket.web.api.v1 import auth as api_v1_auth
from skriptoteket.web.api.v1 import catalog as api_v1_catalog
from skriptoteket.web.api.v1 import tools as api_v1_tools
from skriptoteket.web.auth.dependencies import require_user
from skriptoteket.web.pages import admin_scripting as admin_scripting_pages
from skriptoteket.web.pages import admin_tools as admin_tools_pages
from skriptoteket.web.pages import auth as auth_pages
from skriptoteket.web.pages import browse as browse_pages
from skriptoteket.web.pages import curated_apps as curated_apps_pages
from skriptoteket.web.pages import home as home_pages
from skriptoteket.web.pages import my_runs as my_runs_pages
from skriptoteket.web.pages import my_tools as my_tools_pages
from skriptoteket.web.pages import spa_islands as spa_islands_pages
from skriptoteket.web.pages import suggestions as suggestions_pages
from skriptoteket.web.pages import tools as tools_pages
from skriptoteket.web.routes import editor as editor_routes
from skriptoteket.web.routes import interactive_tools as interactive_tools_routes
from skriptoteket.web.routes import spa_fallback

router = APIRouter()
router.include_router(auth_pages.router)

router.include_router(api_v1_auth.router)
router.include_router(api_v1_catalog.router)
router.include_router(api_v1_tools.router)
router.include_router(editor_routes.router)
router.include_router(interactive_tools_routes.router)

protected = APIRouter(dependencies=[Depends(require_user)])
protected.include_router(home_pages.router)
protected.include_router(browse_pages.router)
protected.include_router(curated_apps_pages.router)
protected.include_router(tools_pages.router)
protected.include_router(my_runs_pages.router)
protected.include_router(my_tools_pages.router)
protected.include_router(suggestions_pages.router)
protected.include_router(spa_islands_pages.router)
protected.include_router(admin_tools_pages.router)
protected.include_router(admin_scripting_pages.router)
router.include_router(protected)

# SPA history fallback - MUST be last to avoid intercepting API routes
router.include_router(spa_fallback.router)
