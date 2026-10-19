"""HTTP/DI skeleton using in-memory storage and real codec/QTI writer, not browser proof."""

from io import BytesIO
from unittest.mock import Mock
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import httpx
from dishka import make_async_container
from fastapi import FastAPI
from starlette_dishka import setup_dishka

from skriptoteket.application.curated_apps.exam_workspace import ExamWorkspaceDocumentResponse
from skriptoteket.application.curated_apps.exam_workspace_history import (
    ExamWorkspaceHistoryDocumentResponse,
    ExamWorkspaceHistoryResponse,
    ExamWorkspaceUndoStepResponse,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_exports import (
    ExportExamWorkspaceDocumentHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_parents import (
    ExamWorkspaceParentsHandler,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_xml import QTI_NAMESPACE
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import NativeExamDocument
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_parent import parent_points
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
    NativeParseOrigin,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_qti_writer import (
    ExamNetQtiPackageWriter,
)
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.exam_conversion import ExamNetPdfRendererProtocol
from skriptoteket.protocols.exam_workspace import (
    ExamPrintRendererProtocol,
    ExamWorkspaceDocxWriterProtocol,
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
from tests.unit.application.curated_apps.handlers.test_exam_workspace_documents import (
    _actor,
    _Env,
)
from tests.unit.application.curated_apps.handlers.test_exam_workspace_history_contract import (
    _undo_handler,
)
from tests.unit.application.curated_apps.test_exam_workspace_exports import _reviewed
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import plain_body
from tests.unit.domain.curated_apps.exam_workspace.recorded_native_exam_support import (
    recorded_items,
)
from tests.unit.web.parent_skeleton_test_support import SkeletonProvider
from tests.unit.web.test_apps_exam_workspace_answer_key_suggestions_api import FakeRegistry


async def build_parent_skeleton_package() -> tuple[bytes, NativeExamDocument]:
    """Seed real DOCX-import output; exercise HTTP validation, DI, save/reopen/export."""
    env = _Env()
    actor = _actor()
    imported = await env.seed_document(actor=actor)
    assert imported.document.origin.kind == "docx_import"
    lineage_id = imported.document.document_id
    undo_steps = _undo_handler(env)
    handler = ExamWorkspaceParentsHandler(reader=env.get_handler, undo_steps=undo_steps)
    exporter = ExportExamWorkspaceDocumentHandler(
        vault_files=env.vault_files,
        codec=env.codec,
        store=env.store,
        qti_writer=ExamNetQtiPackageWriter(),
        pdf_renderer=Mock(spec=ExamNetPdfRendererProtocol),
        docx_writer=Mock(spec=ExamWorkspaceDocxWriterProtocol),
        print_renderer=Mock(spec=ExamPrintRendererProtocol),
    )
    container = make_async_container(
        SkeletonProvider(),
        context={
            CuratedAppRegistryProtocol: FakeRegistry(),
            GetExamWorkspaceDocumentHandlerProtocol: env.get_handler,
            SaveExamWorkspaceDocumentHandlerProtocol: env.save_handler,
            ExamWorkspaceParentsHandlerProtocol: handler,
            StoreExamWorkspaceUndoStepHandlerProtocol: undo_steps,
            ExportExamWorkspaceDocumentHandlerProtocol: exporter,
        },
    )
    app = FastAPI()
    app.middleware("http")(error_handler_middleware)
    app.include_router(documents_api.router)
    app.include_router(parents_api.router)
    # Identity ceremonies are outside this fixture; owner scoping still uses this actor.
    app.dependency_overrides[require_app_user_api] = lambda: actor
    setup_dishka(container, app)
    path = f"/api/v1/apps/documents.conversion_hub/exam-workspace/documents/{lineage_id}"
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            reviewed = _reviewed(imported.document).model_copy(update={"revision": 2})
            response = await client.put(
                path,
                json={
                    "expected_revision": 1,
                    "document": reviewed.model_dump(mode="json"),
                    "position_step_id": str(lineage_id),
                },
            )
            assert response.status_code == 200, response.text
            saved_initial = ExamWorkspaceDocumentResponse.model_validate(response.json())
            # Seed a real autosave: file-only command writes otherwise appear to work.
            draft = saved_initial.document.model_copy(update={"title": "Latest editor draft"})
            response = await client.post(
                path + "/autosaves",
                json={
                    "expected_cursor": str(saved_initial.history_cursor),
                    "document": draft.model_dump(mode="json"),
                },
            )
            assert response.status_code == 200, response.text
            initial_step = ExamWorkspaceUndoStepResponse.model_validate(response.json())
            cursor = initial_step.history.cursor
            # Spara changed the imported baseline. The next autosave retains that
            # saved predecessor as well as the draft, so undo cannot skip it.
            assert len(initial_step.history.step_ids) == 2
            predecessor = await client.get(
                path + "/history/" + str(initial_step.history.step_ids[0])
            )
            assert predecessor.status_code == 200, predecessor.text
            assert (
                ExamWorkspaceHistoryDocumentResponse.model_validate(predecessor.json()).document
                == saved_initial.document
            )
            saved_file = env.vault_files.files[imported.summary.vault_file_id]
            original_bytes = await env.store.load(actor=actor, vault_file=saved_file)
            templates = [
                item
                for item in recorded_items()
                if item.kind is NativeExamItemKind.GAP_FILL and len(item.gaps) == 1
            ]
            child = templates[0].model_dump(mode="json")
            # The client supplies content, not identity or sequence.
            del child["item_id"], child["sequence"]
            child["points"] = 2
            response = await client.post(
                path + "/parents",
                json={
                    "expected_cursor": str(cursor),
                    "instruction": [
                        p.model_dump(mode="json") for p in plain_body("Fyll i rätt form av verbet")
                    ],
                    "child": child,
                    "position": 0,
                },
            )
            assert response.status_code == 200, response.text
            created = ExamWorkspaceDocumentResponse.model_validate(response.json())
            assert created.document.revision == 2
            assert created.document.title == draft.title
            assert created.history_cursor != cursor
            response_history = await client.get(path + "/history")
            history = ExamWorkspaceHistoryResponse.model_validate(response_history.json())
            assert history.step_ids == (*initial_step.history.step_ids, created.history_cursor)
            assert history.cursor == created.history_cursor
            assert await env.store.load(actor=actor, vault_file=saved_file) == original_bytes
            reopened_after_command = await client.get(path)
            assert reopened_after_command.status_code == 200, reopened_after_command.text
            assert (
                ExamWorkspaceDocumentResponse.model_validate(reopened_after_command.json()).document
                == created.document
            )
            parent_id = created.document.parents[0].parent_id
            child = templates[1].model_dump(mode="json")
            del child["item_id"], child["sequence"]
            child["points"] = 3
            response = await client.post(
                path + f"/parents/{parent_id}/children",
                json={
                    "expected_cursor": str(created.history_cursor),
                    "child": child,
                    "position": 1,
                },
            )
            assert response.status_code == 200, response.text
            added = ExamWorkspaceDocumentResponse.model_validate(response.json())
            assert added.document.revision == 2
            assert added.history_cursor != created.history_cursor
            assert await env.store.load(actor=actor, vault_file=saved_file) == original_bytes
            response = await client.get(path + "/history/" + str(created.history_cursor))
            assert response.status_code == 200, response.text
            before_add = ExamWorkspaceHistoryDocumentResponse.model_validate(response.json())
            assert before_add.document == created.document
            assert len(before_add.document.parents[0].item_ids) == 1
            response = await client.post(
                path + f"/parents/{parent_id}/children",
                json={
                    "expected_cursor": str(created.history_cursor),
                    "child": child,
                    "position": 0,
                },
            )
            assert response.status_code == 409, response.text
            assert response.json()["error"]["code"] == "CONFLICT"
            response = await client.get(path)
            assert ExamWorkspaceDocumentResponse.model_validate(response.json()) == added
            response = await client.get(path + "/history")
            assert ExamWorkspaceHistoryResponse.model_validate(response.json()).step_ids == (
                *history.step_ids,
                added.history_cursor,
            )
            # The former revision-guarded payload is gone, with no compatibility route.
            response = await client.post(
                path + f"/parents/{parent_id}/children",
                json={
                    "expected_revision": 2,
                    "child": child,
                    "position": 0,
                },
            )
            assert response.status_code == 422, response.text
            third = next(
                i
                for i in recorded_items("svenska_2_grammatik_omprov_variant_1_med_facit")
                if i.kind is NativeExamItemKind.FREE_TEXT
            ).model_dump(mode="json")
            del third["item_id"], third["sequence"]
            response = await client.post(
                path + f"/parents/{parent_id}/children",
                json={
                    "expected_cursor": str(added.history_cursor),
                    "child": third,
                    "position": 2,
                },
            )
            assert response.status_code == 200, response.text
            extended = ExamWorkspaceDocumentResponse.model_validate(response.json())
            first_id, second_id, third_id = extended.document.parents[0].item_ids
            response = await client.put(
                path + f"/parents/{parent_id}/children/order",
                json={
                    "expected_cursor": str(extended.history_cursor),
                    "item_ids": [first_id, third_id, second_id],
                },
            )
            assert response.status_code == 200, response.text
            reordered = ExamWorkspaceDocumentResponse.model_validate(response.json())
            assert reordered.document.revision == 2
            assert reordered.document.parents[0].item_ids == (first_id, third_id, second_id)
            response = await client.request(
                "DELETE",
                path + f"/parents/{parent_id}/children/{third_id}",
                json={"expected_cursor": str(reordered.history_cursor)},
            )
            assert response.status_code == 200, response.text
            reduced = ExamWorkspaceDocumentResponse.model_validate(response.json())
            assert reduced.document.revision == 2
            assert reduced.document.parents[0].item_ids == (first_id, second_id)
            assert await env.store.load(actor=actor, vault_file=saved_file) == original_bytes
            response = await client.get(path + "/history")
            before_save_history = ExamWorkspaceHistoryResponse.model_validate(response.json())
            assert len(before_save_history.step_ids) == 7
            # Spara alone writes command results to the exam file.
            document = reduced.document.model_copy(update={"revision": 3})
            response = await client.put(
                path,
                json={
                    "expected_revision": 2,
                    "document": document.model_dump(mode="json"),
                    "position_step_id": str(before_save_history.position_step_id),
                },
            )
            assert response.status_code == 200, response.text
            saved = ExamWorkspaceDocumentResponse.model_validate(response.json())
            response = await client.get(path)
            assert response.status_code == 200, response.text
            reopened = ExamWorkspaceDocumentResponse.model_validate(response.json())
            assert reopened.document == saved.document
            assert reopened.document.parents == added.document.parents
            stored_file = env.vault_files.files[saved.summary.vault_file_id]
            stored = env.codec.parse(
                content=await env.store.load(actor=actor, vault_file=stored_file)
            )
            assert stored.document == saved.document
            # Spara rotates the guard without creating a step. It is not a branch ID.
            response = await client.get(path + "/history")
            after_save_history = ExamWorkspaceHistoryResponse.model_validate(response.json())
            assert after_save_history.step_ids == before_save_history.step_ids
            assert saved.history_cursor not in after_save_history.step_ids
            response = await client.put(
                path + f"/parents/{parent_id}/children/order",
                json={
                    "expected_cursor": str(saved.history_cursor),
                    "item_ids": [first_id, second_id],
                },
            )
            assert response.status_code == 200, response.text
            after_save_command = ExamWorkspaceDocumentResponse.model_validate(response.json())
            assert after_save_command.document == saved.document
            assert after_save_command.history_cursor != saved.history_cursor
            parent = reopened.document.parents[0]
            assert parent_points(reopened.document, parent) == 5
            assert [reopened.document.item_by_id(i).points for i in parent.item_ids] == [2, 3]
            assert (
                reopened.document.item_by_id(first_id).body
                != reopened.document.item_by_id(second_id).body
            )
            assert all(
                reopened.document.item_by_id(i).review.parse_origin
                is NativeParseOrigin.TEACHER_CREATED
                for i in parent.item_ids
            )
            response = await client.get(path + "/exports/qti", params={"expected_revision": 3})
            assert response.status_code == 200, response.text
            return response.content, reopened.document
    finally:
        await container.close()


async def test_parent_saves_reopens_and_exports_separators_and_independent_child_scores() -> None:
    content, document = await build_parent_skeleton_package()
    parent = document.parents[0]
    ns = {"q": QTI_NAMESPACE}
    with ZipFile(BytesIO(content)) as archive:
        assert all(f"items/{i}.xml" not in archive.namelist() for i in parent.item_ids)
        root = ET.fromstring(archive.read(f"items/{parent.parent_id}.xml"))
    assert QTI_NAMESPACE == "http://www.imsglobal.org/xsd/imsqtiasi_v3p0"
    body = root.find("q:qti-item-body", ns)
    assert body is not None
    blocks = list(body)
    instruction_index = next(
        index
        for index, block in enumerate(blocks)
        if block.tag == f"{{{QTI_NAMESPACE}}}p" and block.text == "Fyll i rätt form av verbet"
    )
    separators = body.findall("q:qti-gap-match-interaction", ns)
    assert all(blocks.index(separator) > instruction_index for separator in separators)
    assert [s.attrib["response-identifier"] for s in separators] == [
        f"{item_id}_SEPARATOR" for item_id in parent.item_ids
    ]
    assert all(len(s) == 0 for s in separators)
    for separator, item_id in zip(separators, parent.item_ids, strict=True):
        sentence = blocks[blocks.index(separator) + 1]
        entries = sentence.findall("q:qti-text-entry-interaction", ns)
        assert entries and all(
            entry.attrib["response-identifier"].startswith(f"{item_id}_") for entry in entries
        )
    declarations = {
        d.attrib["identifier"]: d for d in root.findall("q:qti-response-declaration", ns)
    }
    response_ids = [
        e.attrib["response-identifier"] for e in root.findall(".//q:qti-text-entry-interaction", ns)
    ]
    assert len(response_ids) == len(set(response_ids)) == 2
    mappings = [declarations[i].find("q:qti-mapping/q:qti-map-entry", ns) for i in response_ids]
    assert all(mapping is not None for mapping in mappings)
    assert [mapping.attrib["mapped-value"] for mapping in mappings if mapping is not None] == [
        "2",
        "3",
    ]
    max_score = root.find(
        "q:qti-outcome-declaration[@identifier='MAXSCORE']/q:qti-default-value/q:qti-value", ns
    )
    assert max_score is not None and max_score.text == "5"
    summed = root.findall(".//q:qti-sum/q:qti-map-response", ns)
    assert [entry.attrib["identifier"] for entry in summed] == response_ids
