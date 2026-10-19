"""Public guest export PDF split (F6): the print PDF is not the Exam.net fallback.

The contracted guest surface offers QTI, the student print PDF, DOCX and a
separately named Exam.net fallback PDF. This suite proves through the real
public route that ``pdf`` renders through the student print renderer while
``examnet_pdf`` renders through the Exam.net PDF renderer, and that the two
never share bytes or filenames. ``pdf_facit`` renders through the same print
renderer with the facit variant.
"""

from __future__ import annotations

import hashlib
from collections.abc import AsyncIterator

import httpx
import pytest
from fastapi import FastAPI

from skriptoteket.application.curated_apps.exam_workspace import (
    ExamWorkspaceExportTarget,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_examnet_pdf_contracts import (
    DigiExamExamNetPdfDocument,
)
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.exam_workspace import ExamPrintPreviewPages
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_document,
    make_free_text_item,
)
from tests.unit.web import (
    public_exam_workspace_export_routes_test_support as route_support,
)
from tests.unit.web.public_exam_workspace_command_routes_test_support import (
    FakeAdmitHandler,
)
from tests.unit.web.public_exam_workspace_export_routes_test_support import (
    _BASE,
    RecordingRenderer,
    _multipart,
    _post_export,
    make_export_app,
)

admit = route_support.admit
registry = route_support.registry
client = route_support.client
renderer = route_support.renderer


class _StubPrintRenderer:
    """Stand-in for the student print renderer; records the HTML it renders."""

    def __init__(self) -> None:
        self.html_by_call: list[str] = []

    def render_pdf(self, *, html: str) -> bytes:
        self.html_by_call.append(html)
        digest = hashlib.sha256(html.encode("utf-8")).hexdigest()[:16]
        return b"PRINT-PDF:" + digest.encode("ascii")

    async def render_preview(self, *, html: str) -> ExamPrintPreviewPages:
        raise NotImplementedError("preview is out of scope for the export split")


class _StubExamNetPdfRenderer:
    """Stand-in for the Exam.net conversion PDF renderer."""

    def __init__(self) -> None:
        self.calls = 0

    def render_pdf(self, *, document: DigiExamExamNetPdfDocument) -> bytes:
        self.calls += 1
        return b"EXAMNET-PDF"


class SplitRenderer(RecordingRenderer):
    """The real export renderer with only the two PDF writers stubbed."""

    def __init__(self) -> None:
        super().__init__()
        self.print_stub = _StubPrintRenderer()
        self.examnet_stub = _StubExamNetPdfRenderer()
        self._print_renderer = self.print_stub
        self._pdf_renderer = self.examnet_stub


@pytest.fixture
def app(
    registry: CuratedAppRegistryProtocol,
    admit: FakeAdmitHandler,
    renderer: RecordingRenderer,
) -> FastAPI:
    return make_export_app(registry=registry, admit=admit, renderer=renderer)


@pytest.fixture
def split_renderer() -> SplitRenderer:
    return SplitRenderer()


@pytest.fixture
def split_app(
    registry: CuratedAppRegistryProtocol,
    admit: FakeAdmitHandler,
    split_renderer: SplitRenderer,
) -> FastAPI:
    return make_export_app(registry=registry, admit=admit, renderer=split_renderer)


@pytest.fixture
async def split_client(
    split_app: FastAPI,
) -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=split_app), base_url="http://test"
    ) as client:
        yield client


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "target,media_type,filename,prefix",
    [
        (ExamWorkspaceExportTarget.QTI, "application/zip", "Omprov grammatik.zip", b"PK"),
        (
            ExamWorkspaceExportTarget.PDF,
            "application/pdf",
            "Omprov grammatik.pdf",
            b"%PDF",
        ),
        (
            ExamWorkspaceExportTarget.PDF_FACIT,
            "application/pdf",
            "Omprov grammatik facit.pdf",
            b"%PDF",
        ),
        (
            ExamWorkspaceExportTarget.DOCX,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "Omprov grammatik.docx",
            b"PK",
        ),
        (
            ExamWorkspaceExportTarget.EXAMNET_PDF,
            "application/pdf",
            "Omprov grammatik Exam.net.pdf",
            b"%PDF",
        ),
    ],
)
async def test_guest_export_serves_all_five_contracted_targets(
    client: httpx.AsyncClient,
    target: ExamWorkspaceExportTarget,
    media_type: str,
    filename: str,
    prefix: bytes,
) -> None:
    response = await _post_export(
        client, target=target, files=_multipart(make_document(make_free_text_item()))
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == media_type
    assert response.headers["content-disposition"] == (f'attachment; filename="{filename}"')
    assert response.content.startswith(prefix)


@pytest.mark.asyncio
async def test_guest_print_pdf_uses_the_student_print_renderer(
    split_client: httpx.AsyncClient,
    split_renderer: SplitRenderer,
) -> None:
    client = split_client
    response = await _post_export(
        client,
        target=ExamWorkspaceExportTarget.PDF,
        files=_multipart(make_document(make_free_text_item())),
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"] == (
        'attachment; filename="Omprov grammatik.pdf"'
    )
    assert response.content.startswith(b"PRINT-PDF:")
    assert split_renderer.examnet_stub.calls == 0
    assert len(split_renderer.print_stub.html_by_call) == 1


@pytest.mark.asyncio
async def test_guest_examnet_pdf_uses_the_examnet_renderer_not_the_print_renderer(
    split_client: httpx.AsyncClient,
    split_renderer: SplitRenderer,
) -> None:
    client = split_client
    document = make_document(make_free_text_item())
    print_response = await _post_export(
        client,
        target=ExamWorkspaceExportTarget.PDF,
        files=_multipart(document),
    )
    fallback_response = await _post_export(
        client,
        target=ExamWorkspaceExportTarget.EXAMNET_PDF,
        files=_multipart(document),
    )

    assert print_response.status_code == 200
    assert fallback_response.status_code == 200
    assert fallback_response.headers["content-disposition"] == (
        'attachment; filename="Omprov grammatik Exam.net.pdf"'
    )
    assert fallback_response.content == b"EXAMNET-PDF"
    assert print_response.content != fallback_response.content
    assert split_renderer.examnet_stub.calls == 1
    assert len(split_renderer.print_stub.html_by_call) == 1


@pytest.mark.asyncio
async def test_guest_facit_pdf_uses_the_print_renderer_with_a_different_variant(
    split_client: httpx.AsyncClient,
    split_renderer: SplitRenderer,
) -> None:
    client = split_client
    document = make_document(make_free_text_item())
    student_response = await _post_export(
        client, target=ExamWorkspaceExportTarget.PDF, files=_multipart(document)
    )
    facit_response = await _post_export(
        client,
        target=ExamWorkspaceExportTarget.PDF_FACIT,
        files=_multipart(document),
    )

    assert student_response.status_code == 200
    assert facit_response.status_code == 200
    assert facit_response.headers["content-disposition"] == (
        'attachment; filename="Omprov grammatik facit.pdf"'
    )
    assert facit_response.content.startswith(b"PRINT-PDF:")
    assert student_response.content != facit_response.content
    assert split_renderer.examnet_stub.calls == 0
    assert len(split_renderer.print_stub.html_by_call) == 2
    assert split_renderer.print_stub.html_by_call[0] != split_renderer.print_stub.html_by_call[1]


@pytest.mark.asyncio
async def test_guest_export_checklist_route_is_unchanged_by_the_pdf_split(
    client: httpx.AsyncClient,
) -> None:
    response = await client.post(
        f"{_BASE}/export-checklist",
        files=_multipart(make_document(make_free_text_item())),
    )

    assert response.status_code == 200
    assert response.json() == {"entries": [], "inline_choice_min_options": 2}
