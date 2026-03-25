from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ParsedStudentRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    full_name: str
    given_name: str | None = None
    family_name: str | None = None
    row_number: int | None = None


class AmbiguousRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    raw_text: str
    row_number: int | None = None
    reason: str | None = None


class ClassListImportPreview(BaseModel):
    model_config = ConfigDict(frozen=True)

    suggested_class_name: str | None = None
    parsed_students: list[ParsedStudentRow] = Field(default_factory=list)
    ambiguous_rows: list[AmbiguousRow] = Field(default_factory=list)
    file_name: str
