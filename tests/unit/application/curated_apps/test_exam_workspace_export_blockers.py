"""One shared export-gate verdict for the three document responses (R6, F8)."""

from datetime import UTC, datetime
from uuid import uuid4

from skriptoteket.application.curated_apps.exam_workspace import (
    ExamWorkspaceDocumentResponse,
    ExamWorkspaceDocumentSummary,
)
from skriptoteket.application.curated_apps.exam_workspace_history import (
    ExamWorkspaceHistoryResponse,
    ExamWorkspaceUndoStepResponse,
)
from skriptoteket.application.curated_apps.public_exam_workspace import (
    PublicExamDocumentCommandResponse,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_export_rules import (
    NativeExportBlocker,
    native_export_blockers,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_document,
    make_gap_fill_item,
)


def _clean_document() -> NativeExamDocument:
    return make_document(make_gap_fill_item())


def _blocked_document() -> NativeExamDocument:
    return make_document(make_gap_fill_item()).model_copy(update={"title": "?!..."})


def _workspace_response(
    document: NativeExamDocument,
    export_blockers: tuple[NativeExportBlocker, ...] | None = None,
) -> ExamWorkspaceDocumentResponse:
    extra: dict[str, tuple[NativeExportBlocker, ...]] = (
        {} if export_blockers is None else {"export_blockers": export_blockers}
    )
    return ExamWorkspaceDocumentResponse(
        document=document,
        saved_document=document,
        summary=ExamWorkspaceDocumentSummary(
            lineage_id=document.document_id,
            version=document.revision,
            vault_file_id=uuid4(),
            name="Prov.provdokument.zip",
            saved_at=datetime(2026, 10, 17, tzinfo=UTC),
            course_key=None,
            title=document.title,
        ),
        history_cursor=uuid4(),
        notes=(),
        conversion=None,
        **extra,
    )


def _workspace_payload(document: NativeExamDocument) -> dict[str, object]:
    response = _workspace_response(document)
    payload = response.model_dump()
    payload.pop("export_blockers")
    return payload


def _public_payload(document: NativeExamDocument) -> dict[str, object]:
    return {"document": document.model_dump()}


def _undo_payload(document: NativeExamDocument) -> dict[str, object]:
    cursor = uuid4()
    return {
        "document": document.model_dump(),
        "history": {
            "cursor": str(cursor),
            "baseline_step_id": str(cursor),
            "step_ids": [],
            "position_step_id": str(cursor),
        },
    }


def _bogus_blocker() -> NativeExportBlocker:
    return NativeExportBlocker(item_id="item_001", reason="missing_points")


class TestSharedExportBlockersVerdict:
    def test_workspace_response_derives_blockers(self) -> None:
        assert _workspace_response(_clean_document()).export_blockers == ()
        blocked = _blocked_document()
        assert _workspace_response(blocked).export_blockers == native_export_blockers(blocked)
        assert _workspace_response(blocked).export_blockers == (
            NativeExportBlocker(item_id=None, reason="title_without_text"),
        )

    def test_public_response_derives_blockers(self) -> None:
        assert PublicExamDocumentCommandResponse(document=_clean_document()).export_blockers == ()
        blocked = _blocked_document()
        response = PublicExamDocumentCommandResponse(document=blocked)
        assert response.export_blockers == native_export_blockers(blocked)
        assert response.export_blockers == (
            NativeExportBlocker(item_id=None, reason="title_without_text"),
        )

    def test_undo_response_derives_blockers(self) -> None:
        cursor = uuid4()
        history = ExamWorkspaceHistoryResponse(
            cursor=cursor,
            baseline_step_id=cursor,
            step_ids=(),
            position_step_id=cursor,
        )
        clean_response = ExamWorkspaceUndoStepResponse(document=_clean_document(), history=history)
        assert clean_response.export_blockers == ()
        blocked = _blocked_document()
        response = ExamWorkspaceUndoStepResponse(document=blocked, history=history)
        assert response.export_blockers == native_export_blockers(blocked)
        assert response.export_blockers == (
            NativeExportBlocker(item_id=None, reason="title_without_text"),
        )

    def test_dict_document_is_validated_once(self) -> None:
        blocked = _blocked_document()
        workspace = ExamWorkspaceDocumentResponse.model_validate(
            {**_workspace_payload(blocked), "document": blocked.model_dump()}
        )
        assert isinstance(workspace.document, NativeExamDocument)
        assert workspace.document == blocked
        assert workspace.export_blockers == native_export_blockers(blocked)

        public = PublicExamDocumentCommandResponse.model_validate(_public_payload(blocked))
        assert isinstance(public.document, NativeExamDocument)
        assert public.document == blocked
        assert public.export_blockers == native_export_blockers(blocked)

        undo = ExamWorkspaceUndoStepResponse.model_validate(_undo_payload(blocked))
        assert isinstance(undo.document, NativeExamDocument)
        assert undo.document == blocked
        assert undo.export_blockers == native_export_blockers(blocked)

    def test_caller_supplied_blockers_are_replaced(self) -> None:
        clean = _clean_document()
        assert _workspace_response(clean, (_bogus_blocker(),)).export_blockers == ()
        assert (
            PublicExamDocumentCommandResponse(
                document=clean, export_blockers=(_bogus_blocker(),)
            ).export_blockers
            == ()
        )
        cursor = uuid4()
        history = ExamWorkspaceHistoryResponse(
            cursor=cursor,
            baseline_step_id=cursor,
            step_ids=(),
            position_step_id=cursor,
        )
        assert (
            ExamWorkspaceUndoStepResponse(
                document=clean, history=history, export_blockers=(_bogus_blocker(),)
            ).export_blockers
            == ()
        )


class TestExportBlockersSerializationSchema:
    def test_workspace_schema_lists_optional_blockers(self) -> None:
        schema = ExamWorkspaceDocumentResponse.model_json_schema(mode="serialization")
        assert set(schema["properties"]) == {
            "document",
            "saved_document",
            "summary",
            "history_cursor",
            "notes",
            "conversion",
            "export_blockers",
        }
        assert sorted(schema["required"]) == [
            "conversion",
            "document",
            "history_cursor",
            "saved_document",
            "summary",
        ]
        assert schema["properties"]["export_blockers"]["default"] == []

    def test_public_schema_lists_optional_blockers(self) -> None:
        schema = PublicExamDocumentCommandResponse.model_json_schema(mode="serialization")
        assert set(schema["properties"]) == {"document", "export_blockers"}
        assert sorted(schema["required"]) == ["document"]
        assert schema["properties"]["export_blockers"]["default"] == []

    def test_undo_schema_keeps_readonly_blockers(self) -> None:
        schema = ExamWorkspaceUndoStepResponse.model_json_schema(mode="serialization")
        assert set(schema["properties"]) == {"document", "history", "export_blockers"}
        assert sorted(schema["required"]) == ["document", "history"]
        blockers = schema["properties"]["export_blockers"]
        assert blockers["default"] == []
        assert blockers["readOnly"] is True
        assert (
            blockers["description"]
            == "The export gate's verdict on the stored step, for the workspace's blocker rows."
        )
