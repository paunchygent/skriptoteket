"""One-question retry: saved source authority, one converter call, one replacement item.

TASK-SKRIPT-39-05-09 D1. The handler reads the question's stored ``retry_source`` from the
saved head revision — never from the editor's draft — sends exactly one batch, and returns
the one replacement item. Every converter problem becomes a source-review item instead.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

import pytest
from pydantic import JsonValue

from skriptoteket.application.curated_apps.exam_workspace import (
    RetryExamWorkspaceItemRequest,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_document_store import (
    ExamWorkspaceDocumentStore,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_rounds import (
    DocxBuildRoundExchange,
    DocxBuildRoundFailure,
    DocxRoundReply,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_retry import (
    RetryExamWorkspaceItemHandler,
)
from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMEndpointKind,
    StructuredLLMProviderProfile,
    StructuredLLMRequest,
    StructuredLLMResponse,
    StructuredLLMUsage,
)
from skriptoteket.domain.curated_apps.exam_workspace.container import ExamWorkspaceContainerContent
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import asset_id_for
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeAnswerKey,
    NativeAnswerKeyOrigin,
    NativeAnswerKeySuggestion,
    NativeExamAsset,
    NativeExamDocument,
    NativeExamDocumentOrigin,
    NativeExamItem,
    NativeExamItemKind,
    NativeExamRetryChunk,
    NativeExamRetryImage,
    NativeExamRetryMissingImage,
    NativeExamRetrySource,
    NativeItemReview,
    NativeItemReviewState,
    NativeParagraph,
    NativeParseOrigin,
    NativeTextSegment,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import AuthProvider, Role, User
from skriptoteket.domain.scripting.vault import VaultFile, VaultUsage
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_container import (
    ExamWorkspaceContainerCodec,
)
from tests.fixtures.time_fixtures import FixedClock
from tests.unit.application.curated_apps.handlers.test_conversion_hub_jobs import (
    SequenceIdGenerator,
)
from tests.unit.application.curated_apps.handlers.test_document_converter_artifact_saves import (
    InMemoryVaultFileRepository,
    InMemoryVaultStorage,
    InMemoryVaultUsageRepository,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

_NOW = datetime(2026, 10, 14, 12, 0, tzinfo=UTC)
_ASSET_ID = "asset_0123456789abcdef"
_FINGERPRINT = "a" * 64
_PROFILE = StructuredLLMProviderProfile(
    provider_id="test-provider",
    model="test-model",
    endpoint_kind=StructuredLLMEndpointKind.RESPONSES,
    is_remote=False,
    context_window_tokens=100_000,
    max_output_tokens=4_000,
)


class FakeUow:
    async def __aenter__(self) -> "FakeUow":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None


class LineageVaultFileRepository(InMemoryVaultFileRepository):
    """The unique (user, lineage, version) constraint the real repository has."""

    async def create(self, *, file: VaultFile) -> VaultFile:
        for existing in self.files.values():
            if (
                existing.user_id == file.user_id
                and existing.document_lineage_id == file.document_lineage_id
                and existing.document_version == file.document_version
            ):
                raise DomainError(
                    code=ErrorCode.CONFLICT,
                    message="Dokumentet sparades samtidigt i en annan flik.",
                )
        return await super().create(file=file)


class FakeExchange:
    """Serve one canned reply, or raise, and record every request."""

    def __init__(self) -> None:
        self.reply: dict[str, JsonValue] | None = None
        self.failure: DocxBuildRoundFailure | None = None
        self.requests: list[StructuredLLMRequest] = []

    async def exchange(
        self, request: StructuredLLMRequest, profile: StructuredLLMProviderProfile
    ) -> DocxRoundReply:
        self.requests.append(request)
        if self.failure is not None:
            raise self.failure
        assert self.reply is not None
        return DocxRoundReply(
            response=StructuredLLMResponse(
                content=self.reply,
                finish_reason="completed",
                usage=StructuredLLMUsage(),
            )
        )


def _actor() -> User:
    return User(
        id=uuid4(),
        email="teacher@example.test",
        role=Role.USER,
        auth_provider=AuthProvider.HULEEDU,
        created_at=_NOW,
        updated_at=_NOW,
    )


def _settings() -> Settings:
    return Settings.model_construct(
        VAULT_MAX_FILE_BYTES=5_000_000,
        VAULT_MAX_TOTAL_BYTES=50_000_000,
    )


def _source(
    *,
    anchor: str = "body:0001",
    text: str = "Förklara vattnets kretslopp.",
    key_anchors: tuple[str, ...] = (),
    images: tuple[NativeExamRetryImage, ...] = (),
    label_kind: NativeExamItemKind = NativeExamItemKind.FREE_TEXT,
) -> NativeExamRetrySource:
    return NativeExamRetrySource(
        chunks=(
            NativeExamRetryChunk(
                anchor=anchor,
                kind="paragraph",
                text=text,
                marked_text=text,
                images=images,
            ),
        ),
        key_chunks=tuple(
            NativeExamRetryChunk(
                anchor=key_anchor, kind="paragraph", text="facit", marked_text="facit"
            )
            for key_anchor in key_anchors
        ),
        context_chunks=(),
        label_kind=label_kind,
    )


def _item(
    item_id: str,
    sequence: int,
    *,
    anchor: str,
    text: str = "Förklara vattnets kretslopp.",
    source: NativeExamRetrySource | None = None,
    suggestion: NativeAnswerKeySuggestion | None = None,
) -> NativeExamItem:
    return NativeExamItem(
        item_id=item_id,
        sequence=sequence,
        kind=NativeExamItemKind.FREE_TEXT,
        body=(NativeParagraph(segments=(NativeTextSegment(text=text),)),),
        answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
        review=NativeItemReview(
            state=NativeItemReviewState.REVIEW_REQUIRED,
            parse_origin=NativeParseOrigin.DETERMINISTIC,
            reasons=("Frågetypen kunde inte avgöras.",),
        ),
        source_anchor=anchor,
        retry_source=source,
        ai_suggestion=suggestion,
    )


def _document(
    *,
    lineage_id: UUID,
    revision: int = 1,
    items: tuple[NativeExamItem, ...],
    assets: tuple[NativeExamAsset, ...] = (),
) -> NativeExamDocument:
    return NativeExamDocument(
        document_id=lineage_id,
        revision=revision,
        title="Omprov",
        items=items,
        assets=assets,
        origin=NativeExamDocumentOrigin(kind="created"),
    )


def _retry_reply(
    *,
    anchor: str = "body:0001",
    text: str = "Ny frågetext.",
    kind: str = "free_text",
    outcome: str = "converted",
    conflict_kind: str | None = None,
) -> dict[str, JsonValue]:
    return {
        "title": None,
        "instructions": [],
        "answer_key_anchors": [],
        "items": [
            {
                "source_anchors": [anchor],
                "outcome": outcome,
                "conflict_kind": conflict_kind,
                "review_reason": None,
                "kind": kind,
                "printed_label": None,
                "body": [
                    {
                        "segments": [
                            {"kind": "text", "text": text, "accepted_values": [], "asset_id": None}
                        ]
                    }
                ],
                "points": 2,
                "choices": [],
                "match_left": [],
                "match_right": [],
                "match_pairs": [],
                "marking_guide": None,
            }
        ],
    }


class _Env:
    def __init__(self, *, enabled: bool = True) -> None:
        self.actor = _actor()
        self.vault_files = LineageVaultFileRepository()
        self.vault_usage = InMemoryVaultUsageRepository(
            usage=VaultUsage(user_id=uuid4(), bytes_total=0, updated_at=_NOW)
        )
        self.vault_storage = InMemoryVaultStorage()
        self.codec = ExamWorkspaceContainerCodec()
        self.ids = SequenceIdGenerator([uuid4() for _ in range(20)])
        self.store = ExamWorkspaceDocumentStore(
            vault_files=self.vault_files,
            vault_usage=self.vault_usage,
            vault_storage=self.vault_storage,
            uow=FakeUow(),
            clock=FixedClock(_NOW),
            settings=_settings(),
        )
        self.exchange = FakeExchange()
        self.handler = RetryExamWorkspaceItemHandler(
            vault_files=self.vault_files,
            codec=self.codec,
            store=self.store,
            exchange=cast(DocxBuildRoundExchange, self.exchange),
            profile=_PROFILE,
            enabled=enabled,
        )

    async def seed(
        self, document: NativeExamDocument, *, assets_by_id: dict[str, bytes] | None = None
    ) -> VaultFile:
        return await self.store.save_version(
            actor=self.actor,
            file_id=self.ids.new_uuid(),
            name="omprov.provdokument.zip",
            content=self.codec.build(
                content=ExamWorkspaceContainerContent(
                    document=document, assets_by_id=assets_by_id or {}
                )
            ),
            lineage_id=document.document_id,
            version=document.revision,
        )

    async def retry(
        self,
        document: NativeExamDocument,
        *,
        item_id: str = "item_001",
        kind: NativeExamItemKind = NativeExamItemKind.FREE_TEXT,
    ):
        return await self.handler.handle(
            actor=self.actor,
            lineage_id=document.document_id,
            request=RetryExamWorkspaceItemRequest(document=document, item_id=item_id, kind=kind),
        )


@pytest.fixture()
def env() -> _Env:
    return _Env()


async def test_retry_returns_one_replacement_that_keeps_identity_and_stored_source(
    env: _Env,
) -> None:
    lineage_id = uuid4()
    document = _document(
        lineage_id=lineage_id, items=(_item("item_001", 1, anchor="body:0001", source=_source()),)
    )
    await env.seed(document)
    env.exchange.reply = _retry_reply(text="Ny frågetext.")

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


async def test_retry_reads_the_saved_source_not_the_draft_item(env: _Env) -> None:
    lineage_id = uuid4()
    saved = _document(
        lineage_id=lineage_id, items=(_item("item_001", 1, anchor="body:0001", source=_source()),)
    )
    await env.seed(saved)
    bogus = _source(anchor="body:0001", text="DRAFTENS EGEN TEXT")
    draft_item = saved.items[0].model_copy(update={"retry_source": bogus, "body": ()})
    draft = saved.model_copy(update={"items": (draft_item,)})
    env.exchange.reply = _retry_reply(text="Ny frågetext.")

    response = await env.retry(draft)

    assert response.item.retry_source == saved.items[0].retry_source
    payload = json.loads(env.exchange.requests[0].user_payload)
    assert payload["chunks"][0]["text"] == "Förklara vattnets kretslopp."


async def test_a_disabled_ai_returns_a_source_review_item_without_a_call() -> None:
    env = _Env(enabled=False)
    lineage_id = uuid4()
    document = _document(
        lineage_id=lineage_id, items=(_item("item_001", 1, anchor="body:0001", source=_source()),)
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
    env: _Env,
) -> None:
    lineage_id = uuid4()
    document = _document(
        lineage_id=lineage_id, items=(_item("item_001", 1, anchor="body:0001", source=_source()),)
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
    env: _Env,
) -> None:
    lineage_id = uuid4()
    document = _document(
        lineage_id=lineage_id, items=(_item("item_001", 1, anchor="body:0001", source=_source()),)
    )
    await env.seed(document)
    env.exchange.reply = _retry_reply(
        outcome="type_conflict", kind="free_text", conflict_kind="gap_fill"
    )

    response = await env.retry(document, kind=NativeExamItemKind.FREE_TEXT)

    item = response.item
    assert item.item_id == "item_001"
    assert item.retry_source == document.items[0].retry_source
    assert item.kind is NativeExamItemKind.FREE_TEXT
    assert item.review.state is NativeItemReviewState.REVIEW_REQUIRED
    assert "annan svarstyp" in item.review.reasons[0]


async def test_a_draft_revision_behind_the_saved_head_is_a_conflict(env: _Env) -> None:
    lineage_id = uuid4()
    document = _document(
        lineage_id=lineage_id, items=(_item("item_001", 1, anchor="body:0001", source=_source()),)
    )
    await env.seed(document)
    stale = document.model_copy(update={"revision": document.revision + 1})

    with pytest.raises(DomainError) as exc_info:
        await env.retry(stale)

    assert exc_info.value.code is ErrorCode.CONFLICT
    assert env.exchange.requests == []


async def test_an_item_without_a_stored_source_is_rejected(env: _Env) -> None:
    lineage_id = uuid4()
    document = _document(
        lineage_id=lineage_id, items=(_item("item_001", 1, anchor="body:0001", source=None),)
    )
    await env.seed(document)

    with pytest.raises(DomainError) as exc_info:
        await env.retry(document)

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert env.exchange.requests == []


async def test_an_item_outside_the_saved_document_is_not_found(env: _Env) -> None:
    lineage_id = uuid4()
    document = _document(
        lineage_id=lineage_id, items=(_item("item_001", 1, anchor="body:0001", source=_source()),)
    )
    await env.seed(document)

    with pytest.raises(DomainError) as exc_info:
        await env.retry(document, item_id="item_009")

    assert exc_info.value.code is ErrorCode.NOT_FOUND


async def test_a_stale_suggestion_is_dropped_by_the_replacement(env: _Env) -> None:
    lineage_id = uuid4()
    suggestion = NativeAnswerKeySuggestion(
        correct_choice_ids=("choice_001",),
        fingerprint=_FINGERPRINT,
        provider_profile_id="provider",
        model="model",
        prompt_template_version="v1",
    )
    document = _document(
        lineage_id=lineage_id,
        items=(_item("item_001", 1, anchor="body:0001", source=_source(), suggestion=suggestion),),
    )
    await env.seed(document)
    env.exchange.reply = _retry_reply(text="Ny frågetext.")

    response = await env.retry(document)

    assert document.items[0].ai_suggestion is not None
    assert response.item.ai_suggestion is None


async def test_the_replacement_keeps_the_draft_items_place(env: _Env) -> None:
    lineage_id = uuid4()
    document = _document(
        lineage_id=lineage_id,
        items=(
            _item("item_001", 1, anchor="body:0001", source=_source()),
            _item("item_002", 2, anchor="body:0002", source=_source(anchor="body:0002")),
        ),
    )
    await env.seed(document)
    env.exchange.reply = _retry_reply(anchor="body:0002", text="Andra frågan, omtolkat.")

    response = await env.retry(document, item_id="item_002")

    assert response.item.item_id == "item_002"
    assert response.item.sequence == 2
    assert response.item.source_anchor == "body:0002"


async def test_a_saved_picture_is_rebuilt_into_the_converter_request(env: _Env) -> None:
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
    document = _document(
        lineage_id=lineage_id,
        items=(
            _item(
                "item_001",
                1,
                anchor="body:0007",
                text="Frågan har en bild.",
                source=_source(anchor="body:0007", text="", images=(image,)),
            ),
        ),
        assets=(asset,),
    )
    await env.seed(document, assets_by_id={asset_id: payload})
    env.exchange.reply = _retry_reply(anchor="body:0007", text="Frågan med bild.")

    await env.retry(document)

    request_payload = json.loads(env.exchange.requests[0].user_payload)
    assert request_payload["chunks"][0]["text"] == f'<image asset_id="{asset_id}"/>'


@pytest.mark.parametrize("source_part", ["chunks", "key_chunks", "context_chunks"])
async def test_a_saved_missing_picture_stays_review_only_without_an_exchange(
    env: _Env,
    source_part: str,
) -> None:
    source = _source()
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
    source = source.model_copy(update={source_part: (missing,)})
    document = _document(
        lineage_id=uuid4(), items=(_item("item_001", 1, anchor="body:0001", source=source),)
    )
    await env.seed(document)
    # The request cannot clear the saved original's loss marker.
    draft = document.model_copy(
        update={"items": (document.items[0].model_copy(update={"retry_source": _source()}),)}
    )
    response = await env.retry(draft)
    assert env.exchange.requests == []
    assert response.item.review.state is NativeItemReviewState.REVIEW_REQUIRED
    assert any("image3.emf" in reason for reason in response.item.review.reasons)
    assert response.item.retry_source == source


async def test_the_retry_request_rejects_a_foreign_lineage(env: _Env) -> None:
    lineage_id = uuid4()
    document = _document(
        lineage_id=lineage_id, items=(_item("item_001", 1, anchor="body:0001", source=_source()),)
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
