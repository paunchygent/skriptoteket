"""One-question retry: the saved revision's stored source is the only authority.

TASK-SKRIPT-39-05-09 D1. These tests fix what the handler may read and reject: the saved
head revision's stored ``NativeExamRetrySource``, never the editor's draft; the saved
picture manifest and container payloads, never a loss the draft hides. Which replacement
comes out of the converter is proved beside this module.
"""

from __future__ import annotations

import hashlib
import json
from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.exam_workspace import (
    RetryExamWorkspaceItemRequest,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import asset_id_for
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamAsset,
    NativeExamItemKind,
    NativeExamRetryChunk,
    NativeExamRetryImage,
    NativeExamRetryMissingImage,
    NativeItemReviewState,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
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
    retry_reply as make_retry_reply,
)
from tests.unit.application.curated_apps.handlers.exam_workspace_docx_retry_fixtures import (
    source as make_source,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


@pytest.fixture()
def env() -> Env:
    return Env()


async def test_retry_reads_the_saved_source_not_the_draft_item(env: Env) -> None:
    lineage_id = uuid4()
    saved = make_document(
        lineage_id=lineage_id,
        items=(make_item("item_001", 1, anchor="body:0001", source=make_source()),),
    )
    await env.seed(saved)
    bogus = make_source(anchor="body:0001", text="DRAFTENS EGEN TEXT")
    draft_item = saved.items[0].model_copy(update={"retry_source": bogus, "body": ()})
    draft = saved.model_copy(update={"items": (draft_item,)})
    env.exchange.reply = make_retry_reply(text="Ny frågetext.")

    response = await env.retry(draft)

    assert response.item.retry_source == saved.items[0].retry_source
    payload = json.loads(env.exchange.requests[0].user_payload)
    assert payload["chunks"][0]["text"] == "Förklara vattnets kretslopp."


async def test_a_draft_revision_behind_the_saved_head_is_a_conflict(env: Env) -> None:
    lineage_id = uuid4()
    document = make_document(
        lineage_id=lineage_id,
        items=(make_item("item_001", 1, anchor="body:0001", source=make_source()),),
    )
    await env.seed(document)
    stale = document.model_copy(update={"revision": document.revision + 1})

    with pytest.raises(DomainError) as exc_info:
        await env.retry(stale)

    assert exc_info.value.code is ErrorCode.CONFLICT
    assert env.exchange.requests == []


async def test_an_item_without_a_stored_source_is_rejected(env: Env) -> None:
    lineage_id = uuid4()
    document = make_document(
        lineage_id=lineage_id, items=(make_item("item_001", 1, anchor="body:0001", source=None),)
    )
    await env.seed(document)

    with pytest.raises(DomainError) as exc_info:
        await env.retry(document)

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert env.exchange.requests == []


async def test_an_item_outside_the_saved_document_is_not_found(env: Env) -> None:
    lineage_id = uuid4()
    document = make_document(
        lineage_id=lineage_id,
        items=(make_item("item_001", 1, anchor="body:0001", source=make_source()),),
    )
    await env.seed(document)

    with pytest.raises(DomainError) as exc_info:
        await env.retry(document, item_id="item_009")

    assert exc_info.value.code is ErrorCode.NOT_FOUND


async def test_a_saved_picture_is_rebuilt_into_the_converter_request(env: Env) -> None:
    lineage_id = uuid4()
    payload = b"png-bytes"
    asset_id = asset_id_for(payload)
    asset = NativeExamAsset(
        asset_id=asset_id,
        sha256=hashlib.sha256(payload).hexdigest(),
        media_type="image/png",
        byte_length=len(payload),
    )
    image = NativeExamRetryImage(asset_id=asset_id, offset=0, marked_offset=0)
    document = make_document(
        lineage_id=lineage_id,
        items=(
            make_item(
                "item_001",
                1,
                anchor="body:0007",
                text="Frågan har en bild.",
                source=make_source(anchor="body:0007", text="", images=(image,)),
            ),
        ),
        assets=(asset,),
    )
    await env.seed(document, assets_by_id={asset_id: payload})
    env.exchange.reply = make_retry_reply(anchor="body:0007", text="Frågan med bild.")

    await env.retry(document)

    request_payload = json.loads(env.exchange.requests[0].user_payload)
    assert request_payload["chunks"][0]["text"] == f'<image asset_id="{asset_id}"/>'


@pytest.mark.parametrize("source_part", ["chunks", "key_chunks", "context_chunks"])
async def test_a_saved_missing_picture_stays_review_only_without_an_exchange(
    env: Env,
    source_part: str,
) -> None:
    retry_source = make_source()
    missing = NativeExamRetryChunk(
        anchor="body:0001" if source_part == "chunks" else "body:0008",
        kind="drawing",
        text="",
        marked_text="",
        missing_images=(
            NativeExamRetryMissingImage(
                reference="/word/media/image3.emf",
                media_type="image/x-emf",
                offset=0,
                marked_offset=0,
            ),
        ),
    )
    retry_source = retry_source.model_copy(update={source_part: (missing,)})
    document = make_document(
        lineage_id=uuid4(),
        items=(make_item("item_001", 1, anchor="body:0001", source=retry_source),),
    )
    await env.seed(document)
    # The request cannot clear the saved original's loss marker.
    draft = document.model_copy(
        update={"items": (document.items[0].model_copy(update={"retry_source": make_source()}),)}
    )
    response = await env.retry(draft)
    assert env.exchange.requests == []
    assert response.item.review.state is NativeItemReviewState.REVIEW_REQUIRED
    assert any("image3.emf" in reason for reason in response.item.review.reasons)
    assert response.item.retry_source == retry_source


async def test_the_retry_request_rejects_a_foreign_lineage(env: Env) -> None:
    lineage_id = uuid4()
    document = make_document(
        lineage_id=lineage_id,
        items=(make_item("item_001", 1, anchor="body:0001", source=make_source()),),
    )
    other = document.model_copy(update={"document_id": uuid4()})

    with pytest.raises(DomainError) as exc_info:
        await env.handler.handle(
            actor=env.actor,
            lineage_id=lineage_id,
            request=RetryExamWorkspaceItemRequest(
                document=other, item_id="item_001", kind=NativeExamItemKind.FREE_TEXT
            ),
        )

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
