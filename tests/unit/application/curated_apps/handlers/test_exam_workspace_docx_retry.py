"""One-question retry: one converter call, one replacement item.

TASK-SKRIPT-39-05-09 D1. The handler sends the question's stored source as exactly one
batch and returns the one replacement item; a disabled conversion, a provider failure, an
invalid reply and a type conflict each return the question's source text as a review item
instead. What the handler may read from the saved revision is proved beside this module.
"""

from __future__ import annotations

import json
from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_rounds import (
    DocxBuildRoundFailure,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeAnswerKeySuggestion,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
    NativeItemReviewState,
    NativeParseOrigin,
)
from tests.unit.application.curated_apps.handlers.exam_workspace_docx_retry_fixtures import (
    FINGERPRINT,
    Env,
)
from tests.unit.application.curated_apps.handlers.exam_workspace_docx_retry_fixtures import (
    document as make_document,
)
from tests.unit.application.curated_apps.handlers.exam_workspace_docx_retry_fixtures import (
    item as make_item,
)
from tests.unit.application.curated_apps.handlers.exam_workspace_docx_retry_fixtures import (
    retry_reply as make_retry_reply,
)
from tests.unit.application.curated_apps.handlers.exam_workspace_docx_retry_fixtures import (
    source as make_source,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


@pytest.fixture()
def env() -> Env:
    return Env()


async def test_retry_returns_one_replacement_that_keeps_identity_and_stored_source(
    env: Env,
) -> None:
    lineage_id = uuid4()
    document = make_document(
        lineage_id=lineage_id,
        items=(make_item("item_001", 1, anchor="body:0001", source=make_source()),),
    )
    await env.seed(document)
    env.exchange.reply = make_retry_reply(text="Ny frågetext.")

    response = await env.retry(document)

    item = response.item
    assert response.lineage_id == lineage_id
    assert item.item_id == "item_001"
    assert item.sequence == 1
    assert item.source_anchor == "body:0001"
    assert item.retry_source == document.items[0].retry_source
    assert item.kind is NativeExamItemKind.FREE_TEXT
    assert item.plain_text_lines() == ("Ny frågetext.",)
    assert len(env.exchange.requests) == 1
    payload = json.loads(env.exchange.requests[0].user_payload)
    assert [chunk["anchor"] for chunk in payload["chunks"]] == ["body:0001"]
    assert [chunk["anchor"] for chunk in payload["context_chunks"]] == []


async def test_a_disabled_ai_returns_a_source_review_item_without_a_call() -> None:
    env = Env(enabled=False)
    lineage_id = uuid4()
    document = make_document(
        lineage_id=lineage_id,
        items=(make_item("item_001", 1, anchor="body:0001", source=make_source()),),
    )
    await env.seed(document)

    response = await env.retry(document)

    item = response.item
    assert item.item_id == "item_001"
    assert item.retry_source == document.items[0].retry_source
    assert item.review.state is NativeItemReviewState.REVIEW_REQUIRED
    assert item.review.reasons == ("AI-tolkning är avstängd. Kontrollera källtexten manuellt.",)
    assert env.exchange.requests == []


async def test_a_provider_failure_returns_the_question_as_a_source_review_item(
    env: Env,
) -> None:
    lineage_id = uuid4()
    document = make_document(
        lineage_id=lineage_id,
        items=(make_item("item_001", 1, anchor="body:0001", source=make_source()),),
    )
    await env.seed(document)
    env.exchange.failure = DocxBuildRoundFailure(
        "AI-tjänsten är inte tillgänglig. Kontrollera källtexten manuellt.",
        code="provider_unavailable",
    )

    response = await env.retry(document)

    item = response.item
    assert item.item_id == "item_001"
    assert item.sequence == 1
    assert item.source_anchor == "body:0001"
    assert item.retry_source == document.items[0].retry_source
    assert item.kind is NativeExamItemKind.FREE_TEXT
    assert item.review.state is NativeItemReviewState.REVIEW_REQUIRED
    assert item.review.parse_origin is NativeParseOrigin.DETERMINISTIC
    assert item.review.reasons == (
        "AI-tjänsten är inte tillgänglig. Kontrollera källtexten manuellt.",
    )
    assert item.plain_text_lines() == ("Förklara vattnets kretslopp.",)


async def test_a_type_conflict_returns_the_question_as_a_source_review_item(
    env: Env,
) -> None:
    lineage_id = uuid4()
    document = make_document(
        lineage_id=lineage_id,
        items=(make_item("item_001", 1, anchor="body:0001", source=make_source()),),
    )
    await env.seed(document)
    env.exchange.reply = make_retry_reply(
        outcome="type_conflict", kind="free_text", conflict_kind="gap_fill"
    )

    response = await env.retry(document, kind=NativeExamItemKind.FREE_TEXT)

    item = response.item
    assert item.item_id == "item_001"
    assert item.retry_source == document.items[0].retry_source
    assert item.kind is NativeExamItemKind.FREE_TEXT
    assert item.review.state is NativeItemReviewState.REVIEW_REQUIRED
    assert "annan svarstyp" in item.review.reasons[0]


async def test_a_stale_suggestion_is_dropped_by_the_replacement(env: Env) -> None:
    lineage_id = uuid4()
    suggestion = NativeAnswerKeySuggestion(
        correct_choice_ids=("choice_001",),
        fingerprint=FINGERPRINT,
        provider_profile_id="provider",
        model="model",
        prompt_template_version="v1",
    )
    document = make_document(
        lineage_id=lineage_id,
        items=(
            make_item(
                "item_001", 1, anchor="body:0001", source=make_source(), suggestion=suggestion
            ),
        ),
    )
    await env.seed(document)
    env.exchange.reply = make_retry_reply(text="Ny frågetext.")

    response = await env.retry(document)

    assert document.items[0].ai_suggestion is not None
    assert response.item.ai_suggestion is None


async def test_the_replacement_keeps_the_draft_items_place(env: Env) -> None:
    lineage_id = uuid4()
    document = make_document(
        lineage_id=lineage_id,
        items=(
            make_item("item_001", 1, anchor="body:0001", source=make_source()),
            make_item("item_002", 2, anchor="body:0002", source=make_source(anchor="body:0002")),
        ),
    )
    await env.seed(document)
    env.exchange.reply = make_retry_reply(anchor="body:0002", text="Andra frågan, omtolkat.")

    response = await env.retry(document, item_id="item_002")

    assert response.item.item_id == "item_002"
    assert response.item.sequence == 2
    assert response.item.source_anchor == "body:0002"
