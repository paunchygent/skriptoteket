"""Reconvert one exam question from its stored source (TASK-SKRIPT-39-05-09 D1).

Purpose:
    The one per-question reconversion the review drawer calls. The saved head revision is
    the source authority: the handler reads the question's stored ``NativeExamRetrySource``
    there — never from the editor's possibly edited draft — and sends exactly that question
    to the converter with the teacher's chosen type. One converter call, one replacement
    item. A reply that cannot become exactly one item — a provider failure, an invalid
    reply, or a type conflict against the chosen kind — returns the question's source text
    as a review item instead. Nothing else is read or changed: no other item, no parent, no
    asset payload, no saved revision.

Relationships:
    - Built by ``di.exam_workspace`` beside the conversion pipeline.
    - Reuses ``convert_batch``/``DocxBuildRoundExchange``, so the strict schema and the
      admission rules are the same as the import conversion's.
    - The pipeline persists ``retry_source`` on every item it builds; this handler is the
      only reader.
"""

from __future__ import annotations

from collections.abc import Mapping
from uuid import UUID

from pydantic import ValidationError

from skriptoteket.application.curated_apps.exam_workspace import (
    ExamWorkspaceItemRetryResponse,
    RetryExamWorkspaceItemRequest,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_document_store import (
    ExamWorkspaceDocumentStore,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build import (
    BatchOutcome,
    convert_batch,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_rounds import (
    DocxBuildExchangeProtocol,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_state import (
    DocxBuildState,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMProviderProfile,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_batches import (
    ConversionBatch,
    QuestionFamily,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_document_language import (
    infer_exam_document_language,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamAsset,
    NativeExamDocument,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_import_record import (
    NativeExamRetryStep,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import (
    NativeExamItem,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_retry_records import (
    NativeExamRetrySource,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_retry_source import (
    context_chunks,
    own_chunks,
    pending_chunks,
    replacement_item,
    source_asset_ids,
    source_missing_picture_reasons,
    source_review_item,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_text import (
    native_exam_document_text,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
    NativeParseOrigin,
)
from skriptoteket.domain.errors import DomainError, ErrorCode, validation_error
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.exam_workspace import ExamWorkspaceContainerCodecProtocol
from skriptoteket.protocols.vault import VaultFileRepositoryProtocol

_RETRY_BATCH_ID = "retry-01"
_DISABLED_REASON = "AI-tolkning är avstängd. Kontrollera källtexten manuellt."
_DEFAULT_FAILURE_REASON = "Frågan kunde inte konverteras om. Kontrollera källtexten manuellt."
_TYPE_CONFLICT_REASON = (
    "AI-tolkningen angav en annan svarstyp än den valda. Kontrollera frågan manuellt."
)
_MULTIPLE_ITEMS_REASON = "AI-svaret gav fler än en fråga. Kontrollera källtexten manuellt."
_INVALID_REASON = "Svaret följer inte provformatet. Kontrollera källtexten manuellt."
_NO_SOURCE_REASON = "Frågan saknar källtext för omkonvertering. Kontrollera frågan manuellt."


def _document_not_found(lineage_id: UUID) -> DomainError:
    return DomainError(
        code=ErrorCode.NOT_FOUND,
        message="Provdokumentet finns inte.",
        details={"lineage_id": str(lineage_id)},
    )


class RetryExamWorkspaceItemHandler:
    """Reconvert one question from the saved revision's stored source."""

    def __init__(
        self,
        *,
        vault_files: VaultFileRepositoryProtocol,
        codec: ExamWorkspaceContainerCodecProtocol,
        store: ExamWorkspaceDocumentStore,
        exchange: DocxBuildExchangeProtocol,
        profile: StructuredLLMProviderProfile,
        enabled: bool,
    ) -> None:
        self._vault_files = vault_files
        self._codec = codec
        self._store = store
        self._exchange = exchange
        self._profile = profile
        self._enabled = enabled

    async def handle(
        self,
        *,
        actor: User,
        lineage_id: UUID,
        request: RetryExamWorkspaceItemRequest,
    ) -> ExamWorkspaceItemRetryResponse:
        draft = request.document
        if draft.document_id != lineage_id:
            raise validation_error(
                "Dokumentet hör till en annan provrad.",
                details={"lineage_id": str(lineage_id)},
            )
        async with self._store.transaction(user_id=actor.id, lineage_id=lineage_id):
            await self._vault_files.lock_document_lineage(
                user_id=actor.id, document_lineage_id=lineage_id
            )
            head = await self._vault_files.get_document_head(
                user_id=actor.id, document_lineage_id=lineage_id
            )
            if head is None:
                raise _document_not_found(lineage_id)
            if head.document_version != draft.revision:
                raise DomainError(
                    code=ErrorCode.CONFLICT,
                    message="Dokumentet har ändrats sedan det öppnades.",
                    details={
                        "expected_revision": draft.revision,
                        "current_revision": head.document_version,
                    },
                )
            content = await self._store.load(actor=actor, vault_file=head)
            container = self._codec.parse(content=content)
        saved = container.document
        if saved.document_id != lineage_id or saved.revision != head.document_version:
            raise validation_error(
                "Den sparade dokumentversionen är skadad.",
                details={"lineage_id": str(lineage_id)},
            )
        # Saved evidence governs the source; the working item carries unsaved attempts.
        saved_item = saved.item_by_id(request.item_id)
        draft_item = draft.item_by_id(request.item_id)
        _validate_retry_history(saved_item, draft_item)
        source = saved_item.retry_source
        if source is None:
            raise validation_error(
                _NO_SOURCE_REASON,
                details={"item_id": request.item_id},
            )
        missing = _missing_source_assets(
            source, assets=saved.assets, payloads=container.assets_by_id
        )
        if missing:
            # A source picture the saved revision no longer carries cannot be rebuilt;
            # fail closed instead of silently losing part of the question's source.
            raise validation_error(
                "Den sparade källan saknar bilder för frågan. "
                "Konvertera om provet från originalfilen.",
                details={"item_id": request.item_id, "asset_ids": missing},
            )
        assets = {asset.asset_id: asset for asset in saved.assets}
        payloads = container.assets_by_id
        missing_pictures = source_missing_picture_reasons(source)
        if missing_pictures:
            return ExamWorkspaceItemRetryResponse(
                lineage_id=lineage_id,
                item=_placed(
                    source_review_item(
                        original=saved_item,
                        source=source,
                        assets=assets,
                        payloads=payloads,
                        reason=" ".join(missing_pictures),
                    ),
                    draft_item,
                    original=saved_item,
                    chosen_kind=request.kind,
                    converted=False,
                ),
            )
        if not self._enabled:
            # The conversion kill switch also governs retry: no provider call, the
            # question's own source as a review item instead.
            return ExamWorkspaceItemRetryResponse(
                lineage_id=lineage_id,
                item=_placed(
                    source_review_item(
                        original=saved_item,
                        source=source,
                        assets=assets,
                        payloads=payloads,
                        reason=_DISABLED_REASON,
                    ),
                    draft_item,
                    original=saved_item,
                    chosen_kind=request.kind,
                    converted=False,
                ),
            )
        replacement = await self._reconvert(
            saved=saved,
            assets=assets,
            payloads=payloads,
            saved_item=saved_item,
            draft_item=draft_item,
            source=source,
            kind=request.kind,
        )
        return ExamWorkspaceItemRetryResponse(lineage_id=lineage_id, item=replacement)

    async def _reconvert(
        self,
        *,
        saved: NativeExamDocument,
        assets: Mapping[str, NativeExamAsset],
        payloads: Mapping[str, bytes],
        saved_item: NativeExamItem,
        draft_item: NativeExamItem,
        source: NativeExamRetrySource,
        kind: NativeExamItemKind,
    ) -> NativeExamItem:
        pending = pending_chunks(source, assets=assets, payloads=payloads)
        context = context_chunks(source, assets=assets, payloads=payloads)
        family = QuestionFamily(
            question_id=saved_item.item_id,
            position=0,
            question_anchors=tuple(
                chunk.anchor for chunk in own_chunks(source, assets=assets, payloads=payloads)
            ),
            claims=frozenset(chunk.anchor for chunk in pending),
            reads=frozenset(chunk.anchor for chunk in context),
        )
        batch = ConversionBatch(
            batch_id=_RETRY_BATCH_ID,
            kinds=frozenset({kind}),
            question_ids=(family.question_id,),
            claims=family.claims,
            reads=family.reads,
        )
        state = DocxBuildState(
            saved.document_id,
            saved.document_id,
            saved.origin.source_filename or "prov.docx",
            saved.origin.source_sha256 or "",
            (*pending, *context),
            claimable=frozenset(chunk.anchor for chunk in pending),
            context_anchors=frozenset(chunk.anchor for chunk in context),
            allowed_kinds=frozenset({kind}),
            batch=batch.batch_id,
            questions=(family.question_anchors,),
            document_language=infer_exam_document_language(native_exam_document_text(saved)),
        )
        outcome = await convert_batch(
            state=state,
            batch=batch,
            families={family.question_id: family},
            exchange=self._exchange,
            profile=self._profile,
        )
        produced = _single_item(state, outcome)
        if produced is None:
            review = source_review_item(
                original=saved_item,
                source=source,
                assets=assets,
                payloads=payloads,
                reason=_review_reason(state, outcome),
            )
            return _placed(
                review, draft_item, original=saved_item, chosen_kind=kind, converted=False
            )
        replacement = replacement_item(original=saved_item, produced=produced)
        replacement = _placed(
            replacement,
            draft_item,
            original=saved_item,
            chosen_kind=kind,
            converted=replacement.review.parse_origin is NativeParseOrigin.LLM_PARSED,
        )
        try:
            return NativeExamItem.model_validate(replacement.model_dump())
        except ValidationError:
            review = source_review_item(
                original=saved_item,
                source=source,
                assets=assets,
                payloads=payloads,
                reason=_INVALID_REASON,
            )
            return _placed(
                review, draft_item, original=saved_item, chosen_kind=kind, converted=False
            )


def _missing_source_assets(
    source: NativeExamRetrySource,
    *,
    assets: tuple[NativeExamAsset, ...],
    payloads: Mapping[str, bytes],
) -> list[str]:
    """Source pictures whose saved manifest entry or container payload is gone."""
    referenced = set(source_asset_ids(source))
    declared = {asset.asset_id for asset in assets}
    return sorted(referenced - (declared & set(payloads)))


def _single_item(state: DocxBuildState, outcome: BatchOutcome) -> NativeExamItem | None:
    """The one item the reply admitted, or None when no single item can replace the question."""
    if outcome.conflicts or len(state.accepted) != 1:
        return None
    return state.accepted[0][0]


def _review_reason(state: DocxBuildState, outcome: BatchOutcome) -> str:
    if outcome.conflicts:
        return _TYPE_CONFLICT_REASON
    if len(state.accepted) > 1:
        return _MULTIPLE_ITEMS_REASON
    return next(iter(state.reasons.values()), _DEFAULT_FAILURE_REASON)


def _validate_retry_history(original: NativeExamItem, draft_item: NativeExamItem) -> None:
    """Anchor import facts, but allow teacher retry history to branch after undo.

    Chosen type, answer-key origin and import type-conflict resends cannot change.
    Only the teacher-request tail is working state: it may predate or diverge from
    Spara, or include several unsaved attempts. Wording is copied from the saved
    record by ``_placed``, never trusted from the working document.
    """
    saved = original.import_record
    if saved is None:
        return
    import_end = next(
        (
            index
            for index, step in enumerate(saved.steps)
            if isinstance(step, NativeExamRetryStep) and step.reason == "teacher_request"
        ),
        len(saved.steps),
    )
    current = draft_item.import_record
    if (
        current is None
        or current.steps[:import_end] != saved.steps[:import_end]
        or any(
            not isinstance(step, NativeExamRetryStep) or step.reason != "teacher_request"
            for step in current.steps[import_end:]
        )
    ):
        raise validation_error(
            "Frågans konverteringshistorik stämmer inte med den sparade versionen.",
            details={"item_id": original.item_id},
        )


def _placed(
    item: NativeExamItem,
    draft_item: NativeExamItem,
    *,
    original: NativeExamItem,
    chosen_kind: NativeExamItemKind,
    converted: bool,
) -> NativeExamItem:
    """Keep saved source facts and append to the validated working retry history."""
    record = original.import_record
    if record is not None:
        assert draft_item.import_record is not None  # Checked before any converter call.
        record = record.model_copy(
            update={
                "steps": (
                    *draft_item.import_record.steps,
                    NativeExamRetryStep(
                        reason="teacher_request",
                        from_kind=draft_item.kind,
                        chosen_kind=chosen_kind,
                        outcome="converted" if converted else "review_required",
                    ),
                )
            }
        )
    return item.model_copy(update={"sequence": draft_item.sequence, "import_record": record})
