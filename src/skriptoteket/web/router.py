from fastapi import APIRouter

from skriptoteket.web.api.v1 import admin_tools as api_v1_admin_tools
from skriptoteket.web.api.v1 import apps as api_v1_apps
from skriptoteket.web.api.v1 import auth as api_v1_auth
from skriptoteket.web.api.v1 import catalog as api_v1_catalog
from skriptoteket.web.api.v1 import editor as api_v1_editor
from skriptoteket.web.api.v1 import favorites as api_v1_favorites
from skriptoteket.web.api.v1 import me as api_v1_me
from skriptoteket.web.api.v1 import my_runs as api_v1_my_runs
from skriptoteket.web.api.v1 import my_tools as api_v1_my_tools
from skriptoteket.web.api.v1 import profile as api_v1_profile
from skriptoteket.web.api.v1 import suggestions as api_v1_suggestions
from skriptoteket.web.api.v1 import tools as api_v1_tools
from skriptoteket.web.routes import interactive_tools as interactive_tools_routes
from skriptoteket.web.routes import spa_fallback

router = APIRouter()

router.include_router(api_v1_auth.router)
router.include_router(api_v1_catalog.router)
router.include_router(api_v1_favorites.router)
router.include_router(api_v1_me.router)
router.include_router(api_v1_my_runs.router)
router.include_router(api_v1_my_tools.router)
router.include_router(api_v1_apps.router)
router.include_router(api_v1_profile.router)
router.include_router(api_v1_suggestions.router)
router.include_router(api_v1_tools.router)
router.include_router(api_v1_admin_tools.router)
router.include_router(api_v1_editor.router)
router.include_router(interactive_tools_routes.router)

# SPA history fallback - MUST be last to avoid intercepting API routes
router.include_router(spa_fallback.router)
