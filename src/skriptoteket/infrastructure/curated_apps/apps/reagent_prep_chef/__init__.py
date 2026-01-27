"""Reagensberedning (curated app).

UI policy: `bespoke_required` (a bespoke SPA view must exist; no generic UI fallback).
"""

from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.actions import (
    execute_reagent_prep_chef_action,
)

__all__ = ["execute_reagent_prep_chef_action"]
