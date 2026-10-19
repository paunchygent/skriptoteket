"""Single-question retry settles trailing points wording on the retried item (D2, D7).

Each case drives the real retry handler the way the answer-line gate tests do,
with a scripted reply whose text ends in a points label: with settled points 2
the wording leaves the body, with points 3 it stays and is recorded.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import JsonValue

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_plain_text
from tests.unit.application.curated_apps.handlers.exam_workspace_docx_retry_fixtures import (
    Env,
)
from tests.unit.application.curated_apps.handlers.exam_workspace_docx_retry_fixtures import (
    document as make_document,
)
from tests.unit.application.curated_apps.handlers.exam_workspace_docx_retry_fixtures import (
    item as make_item,
)
from tests.unit.application.curated_apps.handlers.exam_workspace_docx_retry_fixtures import (
    source as make_source,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


def _reply(text: str, points: int | float) -> dict[str, JsonValue]:
    return {
        "title": None,
        "instructions": [],
        "answer_key_anchors": [],
        "items": [
            {
                "source_anchors": ["body:0001"],
                "outcome": "converted",
                "conflict_kind": None,
                "review_reason": None,
                "kind": "free_text",
                "key_source": None,
                "facit_text": None,
                "printed_label": None,
                "body": [
                    {
                        "segments": [
                            {
                                "kind": "text",
                                "text": text,
                                "accepted_values": [],
                                "asset_id": None,
                            }
                        ]
                    }
                ],
                "points": points,
                "choices": [],
                "match_left": [],
                "match_right": [],
                "match_pairs": [],
                "criteria": [],
            }
        ],
    }


async def test_retry_with_matching_points_loses_the_trailing_wording() -> None:
    env = Env()
    source = make_source(text="Svara utförligt och tydligt. (2 p)")
    document = make_document(
        lineage_id=uuid4(),
        items=(make_item("item_001", 1, anchor="body:0001", source=source),),
    )
    await env.seed(document)
    env.exchange.reply = _reply("Svara utförligt och tydligt. (2 p)", 2)

    response = await env.retry(document)

    item = response.item
    assert body_plain_text(item.body) == "Svara utförligt och tydligt."
    assert item.points == 2
    assert item.leftover_points_text is None


async def test_retry_with_differing_points_keeps_the_text_and_records_it() -> None:
    env = Env()
    source = make_source(text="Svara utförligt och tydligt. (2 p)")
    document = make_document(
        lineage_id=uuid4(),
        items=(make_item("item_001", 1, anchor="body:0001", source=source),),
    )
    await env.seed(document)
    env.exchange.reply = _reply("Svara utförligt och tydligt. (2 p)", 3)

    response = await env.retry(document, kind=NativeExamItemKind.FREE_TEXT)

    item = response.item
    assert body_plain_text(item.body) == "Svara utförligt och tydligt. (2 p)"
    assert item.points == 3
    assert item.leftover_points_text == "(2 p)"
