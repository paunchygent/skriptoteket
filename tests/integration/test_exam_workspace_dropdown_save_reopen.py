"""Real PostgreSQL/container and HTTP/DI proof for saved dropdown Lucktext QTI."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from copy import deepcopy
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock
from xml.etree import ElementTree
from zipfile import ZipFile

import httpx
import pytest
from dishka import Provider, Scope, from_context, make_async_container
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from starlette_dishka import setup_dishka

from skriptoteket.application.curated_apps.handlers.exam_workspace_documents import (
    GetExamWorkspaceDocumentHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_export_renderer import (
    ExamWorkspaceExportRenderer,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_exports import (
    ExportExamWorkspaceDocumentHandler,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_xml import QTI_NAMESPACE
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeGapSegment,
    NativeParagraph,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import NativeExamDocument
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_parent import NativeExamParent
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeAnswerKey,
    NativeChoice,
    NativeGap,
)
from skriptoteket.domain.identity.models import User
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_qti_writer import (
    ExamNetQtiPackageWriter,
)
from skriptoteket.infrastructure.vault.local_vault_storage import LocalVaultStorage
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.exam_conversion import ExamNetPdfRendererProtocol
from skriptoteket.protocols.exam_workspace import (
    ExamPrintRendererProtocol,
    ExamWorkspaceDocxWriterProtocol,
    ExportExamWorkspaceDocumentHandlerProtocol,
    GetExamWorkspaceDocumentHandlerProtocol,
    SaveExamWorkspaceDocumentHandlerProtocol,
)
from skriptoteket.web.api.v1 import apps_conversion_hub_exam_workspace as documents_api
from skriptoteket.web.auth.huleedu_app_projection import require_app_user_api
from skriptoteket.web.middleware.error_handler import error_handler_middleware
from tests.fixtures.time_fixtures import FixedClock
from tests.integration.exam_workspace_conversion_support import ConversionWorld
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


class DropdownApiProvider(Provider):
    registry = from_context(provides=CuratedAppRegistryProtocol, scope=Scope.APP)
    reader = from_context(provides=GetExamWorkspaceDocumentHandlerProtocol, scope=Scope.APP)
    writer = from_context(provides=SaveExamWorkspaceDocumentHandlerProtocol, scope=Scope.APP)
    exporter = from_context(provides=ExportExamWorkspaceDocumentHandlerProtocol, scope=Scope.APP)


@asynccontextmanager
async def _client(world: ConversionWorld, actor: User) -> AsyncIterator[httpx.AsyncClient]:
    container = make_async_container(
        DropdownApiProvider(),
        context={
            CuratedAppRegistryProtocol: FakeRegistry(),
            GetExamWorkspaceDocumentHandlerProtocol: GetExamWorkspaceDocumentHandler(
                vault_files=world.vault_files,
                codec=world.codec,
                store=world.store,
                jobs=world.jobs,
                uow=world.uow,
            ),
            SaveExamWorkspaceDocumentHandlerProtocol: editor(world),
            ExportExamWorkspaceDocumentHandlerProtocol: ExportExamWorkspaceDocumentHandler(
                vault_files=world.vault_files,
                codec=world.codec,
                store=world.store,
                renderer=ExamWorkspaceExportRenderer(
                    qti_writer=ExamNetQtiPackageWriter(),
                    pdf_renderer=Mock(spec=ExamNetPdfRendererProtocol),
                    docx_writer=Mock(spec=ExamWorkspaceDocxWriterProtocol),
                    print_renderer=Mock(spec=ExamPrintRendererProtocol),
                ),
            ),
        },
    )
    app = FastAPI()
    app.middleware("http")(error_handler_middleware)
    app.include_router(documents_api.router)
    app.dependency_overrides[require_app_user_api] = lambda: actor
    setup_dishka(container, app)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            yield client
    finally:
        await container.close()


def _dropdown(sequence: int) -> NativeExamItem:
    # The baseline x2 and superscript x² must not become indistinguishable on export.
    formatted = NativeParagraph.model_validate(
        {
            "heading_level": None,
            "segments": [
                {"kind": "text", "text": "x", "marks": []},
                {"kind": "text", "text": "2", "marks": ["superscript"]},
            ],
        }
    )
    return NativeExamItem(
        item_id=f"item_{sequence:03d}",
        sequence=sequence,
        kind="inline_choice",
        points=5,
        body=(
            NativeParagraph(
                heading_level=None,
                segments=(
                    *text_body("Välj potens: ")[0].segments,
                    NativeGapSegment(gap_id="gap_001"),
                    *text_body(" och färg: ")[0].segments,
                    NativeGapSegment(gap_id="gap_002"),
                ),
            ),
        ),
        gaps=(
            NativeGap(
                gap_id="gap_001",
                options=(
                    NativeChoice(choice_id="choice_001", body=text_body("x2")),
                    NativeChoice(choice_id="choice_002", body=(formatted,)),
                    NativeChoice(choice_id="choice_003", body=text_body("2x")),
                ),
                correct_option_id="choice_002",
            ),
            # Reuse local IDs with a different key to catch cross-gap key/list leakage.
            NativeGap(
                gap_id="gap_002",
                options=tuple(
                    NativeChoice(choice_id=key, body=text_body(label))
                    for key, label in (
                        ("choice_001", "röd"),
                        ("choice_002", "grön"),
                        ("choice_003", "blå"),
                    )
                ),
                correct_option_id="choice_003",
            ),
        ),
        answer_key=NativeAnswerKey(origin="teacher_authored"),
        review=review_complete(),
    )


def _assert_qti(package: bytes, *, item_count: int, parented: bool) -> None:
    with ZipFile(BytesIO(package)) as archive:
        roots = [
            ElementTree.fromstring(archive.read(name))
            for name in archive.namelist()
            if name.endswith(".xml") and name != "imsmanifest.xml"
        ]
    interactions = [
        (root, interaction)
        for root in roots
        for interaction in root.findall(".//q:qti-inline-choice-interaction", _NS)
    ]
    assert len(interactions) == item_count * 2
    assert all(root.find(".//q:qti-text-entry-interaction", _NS) is None for root in roots)
    for index, (root, interaction) in enumerate(interactions):
        options = interaction.findall("q:qti-inline-choice", _NS)
        assert len(options) == 3
        assert ["".join(option.itertext()).strip() for option in options] == (
            ["x2", "x2", "2x"] if index % 2 == 0 else ["röd", "grön", "blå"]
        )
        if index % 2 == 0:
            assert options[0].find(".//q:sup", _NS) is None
            superscript = options[1].find(".//q:sup", _NS)
            assert superscript is not None and superscript.text == "2"
        response_id = interaction.attrib["response-identifier"]
        declaration = root.find(f"q:qti-response-declaration[@identifier='{response_id}']", _NS)
        assert declaration is not None
        assert declaration.attrib["cardinality"] == "single"
        assert declaration.attrib["base-type"] == "identifier"
        key = options[1 if index % 2 == 0 else 2].attrib["identifier"]
        assert [
            value.text for value in declaration.findall("q:qti-correct-response/q:qti-value", _NS)
        ] == [key]
        mapping = declaration.find("q:qti-mapping", _NS)
        assert mapping is not None
        assert mapping.attrib == {"default-value": "0", "lower-bound": "0", "upper-bound": "2.5"}
        assert [entry.attrib for entry in mapping.findall("q:qti-map-entry", _NS)] == [
            {"map-key": key, "mapped-value": "2.5"}
        ]
    response_ids = [interaction.attrib["response-identifier"] for _, interaction in interactions]
    assert len(set(response_ids)) == len(response_ids)
    if parented:
        separators = [
            interaction
            for root in roots
            for interaction in root.findall(".//q:qti-gap-match-interaction", _NS)
            if interaction.attrib["response-identifier"].endswith("_SEPARATOR")
        ]
        assert len(separators) == item_count
        assert all(len(separator) == 0 and not separator.text for separator in separators)
        for root in roots:
            item_body = root.find("q:qti-item-body", _NS)
            if item_body is None:
                continue
            blocks = list(item_body)
            for index, block in enumerate(blocks):
                if block in separators:
                    assert (
                        blocks[index + 1].find(".//q:qti-inline-choice-interaction", _NS)
                        is not None
                    )


@pytest.mark.parametrize("parented", [False, True], ids=["standalone", "parent-children"])
async def test_dropdown_save_reopen_and_qti_from_persisted_container(
    session_factory: async_sessionmaker[AsyncSession], tmp_path: Path, parented: bool
) -> None:
    actor = await create_owner(session_factory)
    clock = FixedClock(datetime.now(UTC))
    storage = LocalVaultStorage(vault_root=tmp_path)
    items = tuple(_dropdown(sequence) for sequence in range(1, 3 if parented else 2))
    parents = (
        (
            NativeExamParent(
                parent_id="parent_001",
                place=items[0].sequence - 1,
                instruction=text_body("Välj svar."),
                item_ids=tuple(item.item_id for item in items),
            ),
        )
        if parented
        else ()
    )
    async with session_factory() as session:
        world = ConversionWorld(session, storage, clock)
        seeded = await seed_exam(world, actor)
        document = NativeExamDocument.model_validate(
            seeded.model_copy(
                update={"revision": 2, "items": items, "parents": parents}
            ).model_dump()
        )
        path = _BASE + str(document.document_id)
        payload = document.model_dump(mode="json")
        async with _client(world, actor) as client:
            position_step_id = (await client.get(path + "/history")).json()["position_step_id"]
            for fault in ("wrong-key", "missing-options"):
                invalid = deepcopy(payload)
                gap = invalid["items"][0]["gaps"][0]
                if fault == "wrong-key":
                    gap["correct_option_id"] = "choice_999"
                else:
                    del gap["options"]
                response = await client.put(
                    path,
                    json={
                        "expected_revision": 1,
                        "document": invalid,
                        "position_step_id": position_step_id,
                    },
                )
                assert response.status_code == 422, response.text
                unchanged = await client.get(path)
                assert unchanged.status_code == 200, unchanged.text
                assert unchanged.json()["document"]["revision"] == 1
            response = await client.put(
                path,
                json={
                    "expected_revision": 1,
                    "document": payload,
                    "position_step_id": position_step_id,
                },
            )
            assert response.status_code == 200, response.text
            assert response.json()["document"]["items"] == payload["items"]

    # New session, new handlers and new DI container: no writer identity-map/cache reuse.
    async with session_factory() as session:
        world = ConversionWorld(session, storage, clock)
        async with _client(world, actor) as client:
            response = await client.get(path)
            assert response.status_code == 200, response.text
            reopened = response.json()
            assert reopened["document"] == payload
            assert reopened["saved_document"] == payload
            head = await world.vault_files.get_document_head(
                user_id=actor.id, document_lineage_id=document.document_id
            )
            assert head is not None and head.document_version == 2
            persisted = world.codec.parse(
                content=await world.store.load(actor=actor, vault_file=head)
            )
            assert persisted.document == document
            response = await client.get(path + "/exports/qti", params={"expected_revision": 2})
            assert response.status_code == 200, response.text
            assert response.headers["content-type"] == "application/zip"
            _assert_qti(response.content, item_count=len(items), parented=parented)
