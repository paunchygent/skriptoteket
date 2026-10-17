"""Central-content snapshot and citation aggregation (TASK-SKRIPT-39-08-03)."""

from __future__ import annotations

import unicodedata
from collections.abc import Sequence
from functools import lru_cache
from importlib.resources import files
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

CONTENT_TAG_THRESHOLD = 0.9


class ExamContentItem(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(min_length=1)
    text: str = Field(min_length=1)


class NativeExamContentTag(ExamContentItem):
    origin: Literal["suggested", "teacher"]
    question_ids: tuple[str, ...] = ()


def content_item_id(course_key: str, text: str) -> str:
    """Identity uses the catalog key and canonical Unicode/whitespace/case text."""
    normalized = " ".join(unicodedata.normalize("NFKC", text).casefold().split())
    return f"{course_key}:{normalized}"


@lru_cache(maxsize=1)
def load_exam_content_catalog() -> dict[str, tuple[ExamContentItem, ...]]:
    from pydantic import TypeAdapter

    payload = files(__package__).joinpath("exam_course_catalog_data/content.json")
    return TypeAdapter(dict[str, tuple[ExamContentItem, ...]]).validate_json(
        payload.read_text(encoding="utf-8")
    )


def aggregate_content_tags(
    content_items: Sequence[ExamContentItem],
    choices: Sequence[tuple[str, str | None, float]],
) -> tuple[NativeExamContentTag, ...]:
    """Only a question's winning choice at the threshold becomes a citation."""
    citations: dict[str, list[str]] = {item.id: [] for item in content_items}
    for question_id, content_id, probability in choices:
        if content_id in citations and probability >= CONTENT_TAG_THRESHOLD:
            if question_id not in citations[content_id]:
                citations[content_id].append(question_id)
    return tuple(
        NativeExamContentTag(
            id=item.id, text=item.text, origin="suggested", question_ids=tuple(citations[item.id])
        )
        for item in content_items
        if citations[item.id]
    )
