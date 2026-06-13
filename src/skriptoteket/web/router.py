"""Top-level FastAPI router assembly for Skriptoteket.

This module gathers every API router plus the final SPA history fallback in
one place so route order stays explicit and curated-app slices can register
their bespoke endpoints without leaking concerns across modules.
"""

from fastapi import APIRouter

from skriptoteket.web.api.v1 import admin_tools as api_v1_admin_tools
from skriptoteket.web.api.v1 import admin_users as api_v1_admin_users
from skriptoteket.web.api.v1 import apps as api_v1_apps
from skriptoteket.web.api.v1 import apps_classroom_planner as api_v1_apps_classroom_planner
from skriptoteket.web.api.v1 import (
    apps_classroom_planner_grouping as api_v1_apps_classroom_planner_grouping,
)
from skriptoteket.web.api.v1 import (
    apps_classroom_planner_guest_upgrade as api_v1_apps_classroom_planner_guest_upgrade,
)
from skriptoteket.web.api.v1 import (
    apps_classroom_planner_seating as api_v1_apps_classroom_planner_seating,
)
from skriptoteket.web.api.v1 import (
    apps_classroom_planner_shares as api_v1_apps_classroom_planner_shares,
)
from skriptoteket.web.api.v1 import (
    apps_classroom_planner_smart_rules as api_v1_apps_classroom_planner_smart_rules,
)
from skriptoteket.web.api.v1 import apps_conversion_hub as api_v1_apps_conversion_hub
from skriptoteket.web.api.v1 import (
    apps_conversion_hub_correction_sessions as api_v1_apps_conversion_hub_correction_sessions,
)
from skriptoteket.web.api.v1 import (
    apps_conversion_hub_transcript_saves as api_v1_apps_conversion_hub_transcript_saves,
)
from skriptoteket.web.api.v1 import apps_flunk_out_frenzy as api_v1_apps_flunk_out_frenzy
from skriptoteket.web.api.v1 import apps_reagent_prep_chef as api_v1_apps_reagent_prep_chef
from skriptoteket.web.api.v1 import catalog as api_v1_catalog
from skriptoteket.web.api.v1 import diagnostics as api_v1_diagnostics
from skriptoteket.web.api.v1 import editor as api_v1_editor
from skriptoteket.web.api.v1 import favorites as api_v1_favorites
from skriptoteket.web.api.v1 import me as api_v1_me
from skriptoteket.web.api.v1 import my_runs as api_v1_my_runs
from skriptoteket.web.api.v1 import my_tools as api_v1_my_tools
from skriptoteket.web.api.v1 import profile as api_v1_profile
from skriptoteket.web.api.v1 import public_apps as api_v1_public_apps
from skriptoteket.web.api.v1 import (
    public_apps_classroom_planner as api_v1_public_apps_classroom_planner,
)
from skriptoteket.web.api.v1 import (
    public_apps_classroom_planner_exports as api_v1_public_apps_classroom_planner_exports,
)
from skriptoteket.web.api.v1 import (
    public_apps_classroom_planner_shares as api_v1_public_apps_classroom_planner_shares,
)
from skriptoteket.web.api.v1 import (
    public_apps_classroom_planner_smart as api_v1_public_apps_classroom_planner_smart,
)
from skriptoteket.web.api.v1 import (
    public_apps_exam_converter as api_v1_public_apps_exam_converter,
)
from skriptoteket.web.api.v1 import suggestions as api_v1_suggestions
from skriptoteket.web.api.v1 import tools as api_v1_tools
from skriptoteket.web.api.v1 import vault as api_v1_vault
from skriptoteket.web.routes import (
    classroom_planner_share_pages as classroom_planner_share_pages_routes,
)
from skriptoteket.web.routes import interactive_tools as interactive_tools_routes
from skriptoteket.web.routes import spa_fallback

router = APIRouter()

router.include_router(api_v1_catalog.router)
router.include_router(api_v1_diagnostics.router)
router.include_router(api_v1_favorites.router)
router.include_router(api_v1_me.router)
router.include_router(api_v1_my_runs.router)
router.include_router(api_v1_my_tools.router)
router.include_router(api_v1_apps.router)
router.include_router(api_v1_public_apps.router)
router.include_router(api_v1_public_apps_classroom_planner.router)
router.include_router(api_v1_public_apps_classroom_planner_exports.router)
router.include_router(api_v1_public_apps_classroom_planner_shares.router)
router.include_router(api_v1_public_apps_classroom_planner_smart.router)
router.include_router(api_v1_public_apps_exam_converter.router)
router.include_router(api_v1_apps_classroom_planner.router)
router.include_router(api_v1_apps_classroom_planner_guest_upgrade.router)
router.include_router(api_v1_apps_classroom_planner_smart_rules.router)
router.include_router(api_v1_apps_classroom_planner_grouping.router)
router.include_router(api_v1_apps_classroom_planner_seating.router)
router.include_router(api_v1_apps_classroom_planner_shares.router)
router.include_router(api_v1_apps_flunk_out_frenzy.router)
router.include_router(api_v1_apps_reagent_prep_chef.router)
router.include_router(api_v1_apps_conversion_hub.router)
router.include_router(api_v1_apps_conversion_hub_correction_sessions.router)
router.include_router(api_v1_apps_conversion_hub_transcript_saves.router)
router.include_router(api_v1_profile.router)
router.include_router(api_v1_suggestions.router)
router.include_router(api_v1_tools.router)
router.include_router(api_v1_vault.router)
router.include_router(api_v1_admin_tools.router)
router.include_router(api_v1_admin_users.router)
router.include_router(api_v1_editor.router)
router.include_router(interactive_tools_routes.router)
router.include_router(classroom_planner_share_pages_routes.router)

# SPA history fallback - MUST be last to avoid intercepting API routes
router.include_router(spa_fallback.router)
