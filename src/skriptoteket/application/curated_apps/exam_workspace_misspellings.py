"""Boundary models for deterministic teacher-keyed gap misspellings."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

AnswerValue = Annotated[str, Field(min_length=1, max_length=200)]


class ExamWorkspaceMisspellingsRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    accepted_values: tuple[AnswerValue, ...] = Field(max_length=100)
    other_gold_answers: tuple[AnswerValue, ...] = Field(max_length=1000)
    document_text: str = Field(max_length=1_000_000)

    @field_validator("document_text")
    @classmethod
    def document_text_byte_budget(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 1_000_000:
            raise ValueError("document_text must not exceed 1 MB of UTF-8 text")
        return value


class ExamWorkspaceMisspellingsResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    automatic_values: tuple[str, ...]
