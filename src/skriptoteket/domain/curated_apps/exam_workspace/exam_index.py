"""Exam-owned saved metadata, independent of the document container and vault."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

ExamListOrdering = Literal["course", "newest"]


class ExamIndexEntry(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    owner_user_id: UUID
    lineage_id: UUID
    course_key: str | None
    title: str
    saved_at: datetime
    head_vault_file_id: UUID


class SavedExam(ExamIndexEntry):
    """Index metadata joined to its current vault file."""

    name: str
    version: int
