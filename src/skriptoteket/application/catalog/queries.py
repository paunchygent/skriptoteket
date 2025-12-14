from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from skriptoteket.domain.catalog.models import Category, Profession, Tool


class ListProfessionsQuery(BaseModel):
    model_config = ConfigDict(frozen=True)


class ListProfessionsResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    professions: list[Profession]


class ListAllCategoriesQuery(BaseModel):
    model_config = ConfigDict(frozen=True)


class ListAllCategoriesResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    categories: list[Category]


class ListCategoriesForProfessionQuery(BaseModel):
    model_config = ConfigDict(frozen=True)

    profession_slug: str


class ListCategoriesForProfessionResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    profession: Profession
    categories: list[Category]


class ListToolsByTagsQuery(BaseModel):
    model_config = ConfigDict(frozen=True)

    profession_slug: str
    category_slug: str


class ListToolsByTagsResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    profession: Profession
    category: Category
    tools: list[Tool]
