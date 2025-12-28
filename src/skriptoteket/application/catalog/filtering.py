from __future__ import annotations

from skriptoteket.domain.curated_apps.models import CuratedAppDefinition
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.identity.role_guards import has_at_least_role
from skriptoteket.protocols.catalog import CatalogFilterProtocol


def _normalize_slug(value: str) -> str:
    return value.strip().lower()


def _normalize_slugs(values: list[str] | None) -> set[str] | None:
    if values is None:
        return None
    normalized = {_normalize_slug(value) for value in values if value and value.strip()}
    return normalized or None


def _normalize_search_term(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized.casefold() if normalized else None


def _matches_search(app: CuratedAppDefinition, search_term: str) -> bool:
    haystack = f"{app.title} {app.summary or ''}".casefold()
    return search_term in haystack


def _matches_placements(
    app: CuratedAppDefinition,
    *,
    profession_slugs: set[str] | None,
    category_slugs: set[str] | None,
) -> bool:
    if profession_slugs is None and category_slugs is None:
        return True
    for placement in app.placements:
        profession = _normalize_slug(placement.profession_slug)
        category = _normalize_slug(placement.category_slug)
        if profession_slugs is not None and profession not in profession_slugs:
            continue
        if category_slugs is not None and category not in category_slugs:
            continue
        return True
    return False


class CatalogFilterService(CatalogFilterProtocol):
    def filter_curated_apps(
        self,
        *,
        apps: list[CuratedAppDefinition],
        actor: User,
        profession_slugs: list[str] | None,
        category_slugs: list[str] | None,
        search_term: str | None,
    ) -> list[CuratedAppDefinition]:
        normalized_professions = _normalize_slugs(profession_slugs)
        normalized_categories = _normalize_slugs(category_slugs)
        normalized_search = _normalize_search_term(search_term)

        filtered: list[CuratedAppDefinition] = []
        for app in apps:
            if not has_at_least_role(user=actor, role=app.min_role):
                continue
            if not _matches_placements(
                app,
                profession_slugs=normalized_professions,
                category_slugs=normalized_categories,
            ):
                continue
            if normalized_search is not None and not _matches_search(app, normalized_search):
                continue
            filtered.append(app)
        return filtered
