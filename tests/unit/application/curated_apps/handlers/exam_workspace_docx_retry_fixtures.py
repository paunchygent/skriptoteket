"""Shared fixtures for the one-question retry handler's focused tests.

TASK-SKRIPT-39-05-09 D1. The retry tests split by responsibility — the saved-source
authority tests and the conversion-outcome tests — and both build the same seeded head
revision, fake exchange and request shapes. ``FakeExchange`` satisfies the production
``DocxBuildExchangeProtocol`` structurally, exactly as ``DocxBuildRoundExchange`` does, so
the handler constructor verifies the same contract for the double and for the real seam.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from pydantic import JsonValue

from skriptoteket.application.curated_apps.exam_workspace import (
    ExamWorkspaceItemRetryResponse,
    RetryExamWorkspaceItemRequest,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_document_store import (
    ExamWorkspaceDocumentStore,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_rounds import (
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
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamAsset,
    NativeExamDocument,
    NativeExamDocumentOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import (
    NativeExamItem,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_retry_records import (
    NativeExamRetryChunk,
    NativeExamRetryImage,
    NativeExamRetrySource,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeAnswerKey,
    NativeAnswerKeySuggestion,
    NativeItemReview,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
    NativeItemReviewState,
    NativeParseOrigin,
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

NOW = datetime(2026, 10, 14, 12, 0, tzinfo=UTC)
FINGERPRINT = "a" * 64
PROFILE = StructuredLLMProviderProfile(
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
    """Serve one canned reply, or raise, and record every request.

    Structurally the ``DocxBuildExchangeProtocol`` the real exchange implements: the
    handler's constructor checks this double against the same seam.
    """

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


def actor() -> User:
    return User(
        id=uuid4(),
        email="teacher@example.test",
        role=Role.USER,
        auth_provider=AuthProvider.HULEEDU,
        created_at=NOW,
        updated_at=NOW,
    )


def settings() -> Settings:
    return Settings.model_construct(
        VAULT_MAX_FILE_BYTES=5_000_000,
        VAULT_MAX_TOTAL_BYTES=50_000_000,
    )


def source(
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


def item(
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


def document(
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


def retry_reply(
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
                "points": 2,
                "choices": [],
                "match_left": [],
                "match_right": [],
                "match_pairs": [],
                "criteria": [],
            }
        ],
    }


class Env:
    def __init__(self, *, enabled: bool = True) -> None:
        self.actor = actor()
        self.vault_files = LineageVaultFileRepository()
        self.vault_usage = InMemoryVaultUsageRepository(
            usage=VaultUsage(user_id=uuid4(), bytes_total=0, updated_at=NOW)
        )
        self.vault_storage = InMemoryVaultStorage()
        self.codec = ExamWorkspaceContainerCodec()
        self.ids = SequenceIdGenerator([uuid4() for _ in range(20)])
        self.store = ExamWorkspaceDocumentStore(
            vault_files=self.vault_files,
            vault_usage=self.vault_usage,
            vault_storage=self.vault_storage,
            uow=FakeUow(),
            clock=FixedClock(NOW),
            settings=settings(),
        )
        self.exchange = FakeExchange()
        self.handler = RetryExamWorkspaceItemHandler(
            vault_files=self.vault_files,
            codec=self.codec,
            store=self.store,
            exchange=self.exchange,
            profile=PROFILE,
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
    ) -> ExamWorkspaceItemRetryResponse:
        return await self.handler.handle(
            actor=self.actor,
            lineage_id=document.document_id,
            request=RetryExamWorkspaceItemRequest(document=document, item_id=item_id, kind=kind),
        )


@pytest.fixture()
def env() -> Env:
    return Env()
