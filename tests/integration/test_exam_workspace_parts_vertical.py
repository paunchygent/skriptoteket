"""Real HTTP/database vertical: group, instruct, move out, delete, then export every target.

The parent commands write editor undo steps without touching the exam file; only Spara
persists the document, so the walk saves once after the part is instructed and once
before exporting. QTI, PDF and DOCX run on the real writers so each artifact is inspected.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZipFile

import httpx
import pytest
from dishka import Provider, Scope, from_context, make_async_container
from docx import Document as DocxDocument
from fastapi import FastAPI
from pypdf import PdfReader
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from starlette_dishka import setup_dishka

from skriptoteket.application.curated_apps.exam_workspace import ExamWorkspaceDocumentResponse
from skriptoteket.application.curated_apps.exam_workspace_history import (
    ExamWorkspaceHistoryResponse,
)
from skriptoteket.application.curated_apps.exam_workspace_parents import (
    ExamWorkspaceCreatedPartResponse,
    ExamWorkspaceDeleteResponse,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_documents import (
    GetExamWorkspaceDocumentHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_export_renderer import (
    ExamWorkspaceExportRenderer,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_exports import (
    ExportExamWorkspaceDocumentHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_parents import (
    ExamWorkspaceParentsHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_undo_steps import (
    StoreExamWorkspaceUndoStepHandler,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_xml import QTI_NAMESPACE
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeGapSegment,
    NativeParagraph,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import NativeExamDocument
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_outline import (
    OutlineQuestion,
    document_outline,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeAnswerKey,
    NativeChoice,
    NativeGap,
)
from skriptoteket.domain.identity.models import User
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub import (
    exam_workspace_docx_writer,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_print_renderer import (
    WeasyPrintExamPrintRenderer,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_pdf_renderer import (
    WeasyPrintExamNetPdfRenderer,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_qti_writer import (
    ExamNetQtiPackageWriter,
)
from skriptoteket.infrastructure.vault.local_vault_storage import LocalVaultStorage
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.exam_workspace import (
    ExportExamWorkspaceDocumentHandlerProtocol,
    GetExamWorkspaceDocumentHandlerProtocol,
    SaveExamWorkspaceDocumentHandlerProtocol,
)
from skriptoteket.protocols.exam_workspace_history import StoreExamWorkspaceUndoStepHandlerProtocol
from skriptoteket.protocols.exam_workspace_parents import ExamWorkspaceParentsHandlerProtocol
from skriptoteket.web.api.v1 import apps_conversion_hub_exam_workspace as documents_api
from skriptoteket.web.api.v1 import apps_conversion_hub_exam_workspace_parents as parents_api
from skriptoteket.web.auth.huleedu_app_projection import require_app_user_api
from skriptoteket.web.middleware.error_handler import error_handler_middleware
from tests.fixtures.time_fixtures import FixedClock
from tests.integration.exam_workspace_conversion_support import ConversionWorld, Ids
from tests.integration.exam_workspace_repair_support import editor, seed_exam
from tests.integration.infrastructure.repositories.exam_workspace_test_support import create_owner
from tests.unit.domain.curated_apps.exam_workspace.examnet_qti_export_test_support import (
    review_complete,
    text_body,
)
from tests.unit.web.test_apps_exam_workspace_answer_key_suggestions_api import FakeRegistry

pytestmark = [pytest.mark.integration, pytest.mark.docker, pytest.mark.asyncio(loop_scope="module")]
_BASE = "/api/v1/apps/documents.conversion_hub/exam-workspace/documents/"
_NS = {"q": QTI_NAMESPACE}
_IMSCP_NAMESPACE = "http://www.imsglobal.org/xsd/qti/qtiv3p0/imscp_v1p1"
_INSTRUCTION = "Läs texten och svara."
_LABELS = (
    "Första ledtråden: ",
    "Andra ledtråden: ",
    "Tredje ledtråden: ",
    "Fjärde ledtråden: ",
    "Femte ledtråden: ",
)
# Every item is a keyed Lucktext with points and an answer key: exportable on all targets.
_ITEM_IDS = ("item_001", "item_002", "item_003", "item_004", "item_005")


class PartsVerticalProvider(Provider):
    registry = from_context(provides=CuratedAppRegistryProtocol, scope=Scope.APP)
    reader = from_context(provides=GetExamWorkspaceDocumentHandlerProtocol, scope=Scope.APP)
    writer = from_context(provides=SaveExamWorkspaceDocumentHandlerProtocol, scope=Scope.APP)
    parents = from_context(provides=ExamWorkspaceParentsHandlerProtocol, scope=Scope.APP)
    undo_steps = from_context(provides=StoreExamWorkspaceUndoStepHandlerProtocol, scope=Scope.APP)
    exporter = from_context(provides=ExportExamWorkspaceDocumentHandlerProtocol, scope=Scope.APP)


@asynccontextmanager
async def _client(world: ConversionWorld, actor: User) -> AsyncIterator[httpx.AsyncClient]:
    reader = GetExamWorkspaceDocumentHandler(
        vault_files=world.vault_files,
        codec=world.codec,
        store=world.store,
        jobs=world.jobs,
        uow=world.uow,
    )
    undo_steps = StoreExamWorkspaceUndoStepHandler(
        vault_files=world.vault_files,
        codec=world.codec,
        store=world.store,
        jobs=world.jobs,
        id_generator=Ids(),
    )
    container = make_async_container(
        PartsVerticalProvider(),
        context={
            CuratedAppRegistryProtocol: FakeRegistry(),
            GetExamWorkspaceDocumentHandlerProtocol: reader,
            SaveExamWorkspaceDocumentHandlerProtocol: editor(world),
            ExamWorkspaceParentsHandlerProtocol: ExamWorkspaceParentsHandler(
                reader=reader, undo_steps=undo_steps
            ),
            StoreExamWorkspaceUndoStepHandlerProtocol: undo_steps,
            ExportExamWorkspaceDocumentHandlerProtocol: ExportExamWorkspaceDocumentHandler(
                vault_files=world.vault_files,
                codec=world.codec,
                store=world.store,
                renderer=ExamWorkspaceExportRenderer(
                    qti_writer=ExamNetQtiPackageWriter(),
                    pdf_renderer=WeasyPrintExamNetPdfRenderer(),
                    docx_writer=exam_workspace_docx_writer.ExamWorkspaceDocxWriter(),
                    print_renderer=WeasyPrintExamPrintRenderer(),
                ),
            ),
        },
    )
    app = FastAPI()
    app.middleware("http")(error_handler_middleware)
    app.include_router(documents_api.router)
    app.include_router(parents_api.router)
    app.dependency_overrides[require_app_user_api] = lambda: actor
    setup_dishka(container, app)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            yield client
    finally:
        await container.close()


def _question(sequence: int, label: str) -> NativeExamItem:
    """One exportable keyed Lucktext whose leading text is unique for order assertions."""
    return NativeExamItem(
        item_id=f"item_{sequence:03d}",
        sequence=sequence,
        kind="inline_choice",
        points=5,
        body=(
            NativeParagraph(
                heading_level=None,
                segments=(
                    *text_body(label)[0].segments,
                    NativeGapSegment(gap_id="gap_001"),
                    *text_body(" och ")[0].segments,
                    NativeGapSegment(gap_id="gap_002"),
                ),
            ),
        ),
        gaps=(
            NativeGap(
                gap_id="gap_001",
                options=(
                    NativeChoice(choice_id="choice_001", body=text_body("ett")),
                    NativeChoice(choice_id="choice_002", body=text_body("två")),
                ),
                correct_option_id="choice_001",
            ),
            NativeGap(
                gap_id="gap_002",
                options=(
                    NativeChoice(choice_id="choice_001", body=text_body("tre")),
                    NativeChoice(choice_id="choice_002", body=text_body("fyra")),
                ),
                correct_option_id="choice_002",
            ),
        ),
        answer_key=NativeAnswerKey(origin="teacher_authored"),
        review=review_complete(),
    )


def _outline(document: NativeExamDocument) -> tuple[str, ...]:
    """Top-level order as item ids and ``part:<id>`` markers, through the ordering owner."""
    entries: list[str] = []
    for entry in document_outline(document):
        if isinstance(entry, OutlineQuestion):
            entries.append(entry.item.item_id)
        else:
            entries.append(f"part:{entry.part.parent_id}")
    return tuple(entries)


def _qti_item_roots(package: bytes) -> dict[str, ElementTree.Element]:
    with ZipFile(BytesIO(package)) as archive:
        return {
            name: ElementTree.fromstring(archive.read(name))
            for name in archive.namelist()
            if name.startswith("items/") and name.endswith(".xml") and "/" not in name[6:]
        }


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _assessment_order(package: bytes) -> tuple[str, ...]:
    with ZipFile(BytesIO(package)) as archive:
        root = ElementTree.fromstring(archive.read("assessment.xml"))
    return tuple(
        ref.attrib["href"].removeprefix("items/").removesuffix(".xml")
        for ref in root.findall(".//q:qti-assessment-item-ref", _NS)
    )


def _manifest_item_order(package: bytes) -> tuple[str, ...]:
    with ZipFile(BytesIO(package)) as archive:
        root = ElementTree.fromstring(archive.read("imsmanifest.xml"))
    resource_tag = f"{{{_IMSCP_NAMESPACE}}}resource"
    return tuple(
        resource.attrib["href"].removeprefix("items/").removesuffix(".xml")
        for resource in root.findall(f".//{resource_tag}")
        if resource.attrib["type"] == "imsqti_item_xmlv3p0"
    )


def _assert_qti_information_block(package: bytes, *, part_id: str) -> None:
    roots = _qti_item_roots(package)
    assert f"items/{part_id}.xml" in roots
    carriers = [root for root in roots.values() if _INSTRUCTION in "".join(root.itertext())]
    assert len(carriers) == 1
    information = carriers[0]
    body = information.find("q:qti-item-body", _NS)
    assert body is not None
    assert _INSTRUCTION in "".join(body.itertext())
    # An information block holds text only: no interaction, response, outcome or processing.
    assert not [
        element.tag
        for element in information.iter()
        if _local_name(element.tag).endswith("-interaction")
    ]
    assert information.find("q:qti-response-declaration", _NS) is None
    assert information.find("q:qti-outcome-declaration", _NS) is None
    assert information.find("q:qti-response-processing", _NS) is None
    expected = ("item_001", part_id, "item_002", "item_003", "item_005")
    # The part stands where it sits: after q1, before the following q2.
    assert _assessment_order(package) == expected
    assert _manifest_item_order(package) == expected


def _assert_pdf(content: bytes) -> None:
    assert content.startswith(b"%PDF-")
    text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(content)).pages)
    assert text.count(_INSTRUCTION) == 1
    # The question that follows the part is q2: its printed text comes after the instruction.
    assert text.index(_INSTRUCTION) < text.index("Andra ledtråden:")


def _assert_docx(content: bytes) -> None:
    parsed = DocxDocument(BytesIO(content))
    paragraphs = list(parsed.paragraphs)
    texts = [paragraph.text for paragraph in paragraphs]
    assert texts.count(_INSTRUCTION) == 1
    instruction_index = texts.index(_INSTRUCTION)
    headings = [
        (index, paragraph.text)
        for index, paragraph in enumerate(paragraphs)
        if paragraph.style is not None and paragraph.style.name == "Heading 3"
    ]
    assert [text for _, text in headings] == ["Fråga 1", "Fråga 2", "Fråga 3", "Fråga 4"]
    before = next(index for index, text in headings if text == "Fråga 1")
    after = next(index for index, text in headings if text == "Fråga 2")
    assert before < instruction_index < after


async def test_group_instruct_move_delete_then_export_all_targets(
    session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    actor = await create_owner(session_factory)
    clock = FixedClock(datetime.now(UTC))
    storage = LocalVaultStorage(vault_root=tmp_path)
    items = tuple(_question(sequence, label) for sequence, label in enumerate(_LABELS, start=1))
    async with session_factory() as session:
        world = ConversionWorld(session, storage, clock)
        seeded = await seed_exam(world, actor)
        document = NativeExamDocument.model_validate(
            seeded.model_copy(update={"revision": 2, "items": items, "parents": ()}).model_dump()
        )
        path = _BASE + str(document.document_id)
        async with _client(world, actor) as client:
            history = ExamWorkspaceHistoryResponse.model_validate(
                (await client.get(path + "/history")).json()
            )
            response = await client.put(
                path,
                json={
                    "expected_revision": 1,
                    "document": document.model_dump(mode="json"),
                    "position_step_id": str(history.position_step_id),
                },
            )
            assert response.status_code == 200, response.text
            saved_initial = ExamWorkspaceDocumentResponse.model_validate(response.json())
            assert _outline(saved_initial.document) == _ITEM_IDS
            cursor = str(saved_initial.history_cursor)

            # Step 2: group the non-adjacent q2 and q4 into one part at q2's place.
            response = await client.post(
                path + "/parents/group",
                json={"expected_cursor": cursor, "item_ids": ["item_002", "item_004"]},
            )
            assert response.status_code == 200, response.text
            grouped = ExamWorkspaceCreatedPartResponse.model_validate(response.json())
            part_id = grouped.created_parent_id
            part = grouped.document.parent_of("item_002")
            assert part is not None and part.parent_id == part_id
            assert part.item_ids == ("item_002", "item_004")
            assert grouped.document.parent_of("item_004") is part
            assert _outline(grouped.document) == (
                "item_001",
                f"part:{part_id}",
                "item_003",
                "item_005",
            )
            cursor = str(grouped.history_cursor)

            # Step 3: give the part its instruction through Spara, the normal edit path.
            instructed_part = part.model_copy(update={"instruction": text_body(_INSTRUCTION)})
            edited = grouped.document.model_copy(
                update={
                    "revision": grouped.document.revision + 1,
                    "parents": tuple(
                        instructed_part if value.parent_id == part_id else value
                        for value in grouped.document.parents
                    ),
                }
            )
            history = ExamWorkspaceHistoryResponse.model_validate(
                (await client.get(path + "/history")).json()
            )
            response = await client.put(
                path,
                json={
                    "expected_revision": grouped.document.revision,
                    "document": edited.model_dump(mode="json"),
                    "position_step_id": str(history.position_step_id),
                },
            )
            assert response.status_code == 200, response.text
            instructed = ExamWorkspaceDocumentResponse.model_validate(response.json())
            kept = instructed.document.parent_of("item_002")
            assert kept is not None and kept.instruction == text_body(_INSTRUCTION)
            assert _outline(instructed.document) == (
                "item_001",
                f"part:{part_id}",
                "item_003",
                "item_005",
            )
            cursor = str(instructed.history_cursor)

            # Step 4: move q2 out to standalone directly after the part (R4).
            response = await client.post(
                path + "/parents/move",
                json={"expected_cursor": cursor, "item_id": "item_002", "target_parent_id": None},
            )
            assert response.status_code == 200, response.text
            moved_out = ExamWorkspaceDocumentResponse.model_validate(response.json())
            assert moved_out.document.parent_of("item_002") is None
            remaining = moved_out.document.parent_of("item_004")
            assert remaining is not None and remaining.item_ids == ("item_004",)
            assert _outline(moved_out.document) == (
                "item_001",
                f"part:{part_id}",
                "item_002",
                "item_003",
                "item_005",
            )
            cursor = str(moved_out.history_cursor)

            # Step 5: delete the part's last question; the part stays as an instruction block (G8).
            response = await client.request(
                "DELETE",
                path + f"/parents/{part_id}/children/item_004",
                json={"expected_cursor": cursor},
            )
            assert response.status_code == 200, response.text
            deleted = ExamWorkspaceDeleteResponse.model_validate(response.json())
            assert deleted.removed_parent_id is None
            empty_part = next(
                value for value in deleted.document.parents if value.parent_id == part_id
            )
            assert empty_part.item_ids == ()
            assert empty_part.instruction == text_body(_INSTRUCTION)
            assert _outline(deleted.document) == (
                "item_001",
                f"part:{part_id}",
                "item_002",
                "item_003",
                "item_005",
            )

            # Step 6: Spara, because every export reads the saved head at its revision.
            final = deleted.document.model_copy(update={"revision": deleted.document.revision + 1})
            history = ExamWorkspaceHistoryResponse.model_validate(
                (await client.get(path + "/history")).json()
            )
            response = await client.put(
                path,
                json={
                    "expected_revision": deleted.document.revision,
                    "document": final.model_dump(mode="json"),
                    "position_step_id": str(history.position_step_id),
                },
            )
            assert response.status_code == 200, response.text
            saved = ExamWorkspaceDocumentResponse.model_validate(response.json())
            revision = saved.document.revision
            assert revision == 4

            response = await client.get(
                path + "/exports/qti", params={"expected_revision": revision}
            )
            assert response.status_code == 200, response.text
            assert response.headers["content-type"] == "application/zip"
            _assert_qti_information_block(response.content, part_id=part_id)

            response = await client.get(
                path + "/exports/pdf", params={"expected_revision": revision}
            )
            assert response.status_code == 200, response.text
            assert response.headers["content-type"] == "application/pdf"
            _assert_pdf(response.content)

            response = await client.get(
                path + "/exports/docx", params={"expected_revision": revision}
            )
            assert response.status_code == 200, response.text
            assert response.headers["content-type"].startswith(
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            _assert_docx(response.content)
