"""The student print preview handler: data-URL pages and the blocked path (W5)."""

from __future__ import annotations

import base64
from hashlib import sha256
from uuid import UUID, uuid4

import pytest

from skriptoteket.application.curated_apps.exam_workspace import (
    SaveExamWorkspaceDocumentRequest,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_print_preview import (
    PreviewExamWorkspacePrintHandler,
)
from skriptoteket.domain.curated_apps.exam_workspace.container import (
    ExamWorkspaceContainerContent,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import asset_id_for
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeAssetSegment,
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamAsset,
    NativeExamDocument,
    NativeExamDocumentOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_export_rules import (
    native_export_blockers,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.protocols.exam_workspace import (
    ExamPrintPreviewPages,
    ExamPrintRendererProtocol,
    ExamWorkspaceContainerCodecProtocol,
)
from tests.unit.application.curated_apps.handlers.test_exam_workspace_documents import (
    _actor,
    _Env,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_document_test_support import (
    with_next_revision,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_document,
    make_free_text_item,
    make_single_choice_item,
)

_FIRST_PNG = b"\x89PNG\r\n\x1a\nfirst"
_SECOND_PNG = b"\x89PNG\r\n\x1a\nsecond"


def _data_url(png: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(png).decode("ascii")


class _FakePrintRenderer:
    """Record the print HTML the handler built and return fixed preview pages."""

    def __init__(self) -> None:
        self.html_by_call: list[str] = []

    def render_pdf(self, *, html: str) -> bytes:
        raise AssertionError("the preview handler never renders PDFs")

    async def render_preview(self, *, html: str) -> ExamPrintPreviewPages:
        self.html_by_call.append(html)
        return ExamPrintPreviewPages(
            pages=(_FIRST_PNG, _SECOND_PNG),
            question_pages={"item_001": 0, "item_002": 1},
        )


class _AssetsStrippedCodec:
    """Parse a real container but drop its picture payloads, an unrenderable head."""

    def __init__(self, inner: ExamWorkspaceContainerCodecProtocol) -> None:
        self._inner = inner

    def build(self, *, content: ExamWorkspaceContainerContent) -> bytes:
        return self._inner.build(content=content)

    def parse(self, *, content: bytes) -> ExamWorkspaceContainerContent:
        parsed = self._inner.parse(content=content)
        return ExamWorkspaceContainerContent.model_construct(
            document=parsed.document, assets_by_id={}, notes=parsed.notes
        )


def _preview_handler(
    env: _Env,
    *,
    print_renderer: ExamPrintRendererProtocol | None = None,
    codec: ExamWorkspaceContainerCodecProtocol | None = None,
) -> PreviewExamWorkspacePrintHandler:
    return PreviewExamWorkspacePrintHandler(
        vault_files=env.vault_files,
        codec=codec if codec is not None else env.codec,
        store=env.store,
        print_renderer=print_renderer if print_renderer is not None else _FakePrintRenderer(),
    )


@pytest.fixture()
def env() -> _Env:
    return _Env()


def _draft_document() -> NativeExamDocument:
    """A document the export gate refuses: an unkeyed choice and items without points."""

    choice = make_single_choice_item(origin=NativeAnswerKeyOrigin.ABSENT, correct=()).model_copy(
        update={"points": None}
    )
    free_text = make_free_text_item(sequence=2, item_id="item_002").model_copy(
        update={"points": None}
    )
    return make_document(choice, free_text)


def _document_with_asset() -> tuple[NativeExamDocument, bytes, str]:
    payload = b"picture-bytes"
    asset_id = asset_id_for(payload)
    item = make_free_text_item().model_copy(
        update={
            "body": (
                NativeParagraph(
                    heading_level=None,
                    segments=(
                        NativeTextSegment(text="Se bilden. ", marks=()),
                        NativeAssetSegment(asset_id=asset_id),
                    ),
                ),
            )
        }
    )
    asset = NativeExamAsset(
        asset_id=asset_id,
        sha256=sha256(payload).hexdigest(),
        media_type="image/png",
        byte_length=len(payload),
    )
    document = NativeExamDocument(
        document_id=uuid4(),
        revision=1,
        title="Prov med bild",
        items=(item,),
        assets=(asset,),
        origin=NativeExamDocumentOrigin(kind="created"),
    )
    return document, payload, asset_id


@pytest.mark.asyncio
async def test_ready_returns_page_data_urls_and_question_pages(env: _Env) -> None:
    actor = _actor()
    imported = await env.seed_document(actor=actor, document=_draft_document())
    renderer = _FakePrintRenderer()

    response = await _preview_handler(env, print_renderer=renderer).handle(
        actor=actor, lineage_id=imported.summary.lineage_id, expected_revision=1
    )

    assert response.status == "ready"
    assert response.revision == 1
    assert response.message is None
    assert response.pages == [_data_url(_FIRST_PNG), _data_url(_SECOND_PNG)]
    assert response.question_pages == {"item_001": 0, "item_002": 1}
    assert len(renderer.html_by_call) == 1
    assert "– Elevexemplar</title>" in renderer.html_by_call[0]
    assert "– Facit</title>" not in renderer.html_by_call[0]


@pytest.mark.asyncio
async def test_a_blocked_export_state_still_renders_the_student_copy(env: _Env) -> None:
    actor = _actor()
    document = _draft_document()
    assert native_export_blockers(document), "the draft must be refused by the export gate"
    imported = await env.seed_document(actor=actor, document=document)

    response = await _preview_handler(env).handle(
        actor=actor, lineage_id=imported.summary.lineage_id, expected_revision=1
    )

    assert response.status == "ready"
    assert response.pages


@pytest.mark.asyncio
async def test_missing_picture_payload_returns_blocked_without_raising(env: _Env) -> None:
    actor = _actor()
    document, payload, asset_id = _document_with_asset()
    await env.store.save(
        actor=actor,
        file_id=env.ids.new_uuid(),
        name="prov.provdokument.zip",
        content=env.codec.build(
            content=ExamWorkspaceContainerContent(
                document=document, assets_by_id={asset_id: payload}, notes=()
            )
        ),
        lineage_id=document.document_id,
        version=1,
    )
    renderer = _FakePrintRenderer()

    response = await _preview_handler(
        env, print_renderer=renderer, codec=_AssetsStrippedCodec(env.codec)
    ).handle(actor=actor, lineage_id=document.document_id, expected_revision=1)

    assert response.status == "blocked"
    assert response.revision == 1
    assert response.pages == []
    assert response.question_pages == {}
    assert response.message == "PDF-exporten saknar bilddata för en bild."
    assert renderer.html_by_call == []


@pytest.mark.asyncio
async def test_stale_expected_revision_conflicts_with_the_preview_message(env: _Env) -> None:
    actor = _actor()
    imported = await env.seed_document(actor=actor)
    await env.save_handler.handle(
        actor=actor,
        lineage_id=imported.summary.lineage_id,
        request=SaveExamWorkspaceDocumentRequest(
            expected_revision=1,
            document=with_next_revision(imported.document),
            position_step_id=imported.summary.lineage_id,
        ),
    )

    with pytest.raises(DomainError) as exc_info:
        await _preview_handler(env).handle(
            actor=actor, lineage_id=imported.summary.lineage_id, expected_revision=1
        )

    assert exc_info.value.code is ErrorCode.CONFLICT
    assert (
        exc_info.value.message == "Det sparade provet har ändrats. Förhandsgranskningen uppdateras."
    )
    assert exc_info.value.details == {"expected_revision": 1, "current_revision": 2}


@pytest.mark.asyncio
async def test_unknown_lineage_is_not_found(env: _Env) -> None:
    with pytest.raises(DomainError) as exc_info:
        await _preview_handler(env).handle(
            actor=_actor(), lineage_id=UUID(int=0), expected_revision=1
        )

    assert exc_info.value.code is ErrorCode.NOT_FOUND
