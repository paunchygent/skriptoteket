"""Unit tests for the exam workspace container codec (fail-closed parsing)."""

import hashlib
import io
import json
import zipfile
from uuid import uuid4

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.container import (
    EXAM_WORKSPACE_CONTAINER_SCHEMA_VERSION,
    ExamWorkspaceContainerContent,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
    NativeExamDocumentOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document_json import (
    native_exam_document_json_bytes,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import (
    NativeExamItem,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeAnswerKey,
    NativeItemReview,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
    NativeItemReviewState,
    NativeParseOrigin,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_container import (
    ExamWorkspaceContainerCodec,
)


def _document() -> NativeExamDocument:
    return NativeExamDocument(
        document_id=uuid4(),
        revision=1,
        title="Omprov: grammatik",
        items=(
            NativeExamItem(
                item_id="item_001",
                sequence=1,
                kind=NativeExamItemKind.FREE_TEXT,
                writing_lines=8,
                body=(
                    NativeParagraph(
                        heading_level=None,
                        segments=(NativeTextSegment(text="Resonera om stil.", marks=()),),
                    ),
                ),
                points=4,
                answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
                review=NativeItemReview(
                    state=NativeItemReviewState.REVIEW_COMPLETE,
                    parse_origin=NativeParseOrigin.DETERMINISTIC,
                    confidence=0.9,
                ),
            ),
        ),
        origin=NativeExamDocumentOrigin(kind="created"),
    )


def _rezip_with(content: bytes, *, replace: dict[str, bytes]) -> bytes:
    source = zipfile.ZipFile(io.BytesIO(content))
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as target:
        for name in source.namelist():
            target.writestr(name, replace.get(name, source.read(name)))
        for name, payload in replace.items():
            if name not in source.namelist():
                target.writestr(name, payload)
    return buffer.getvalue()


class TestContainerCodec:
    def test_round_trip(self) -> None:
        codec = ExamWorkspaceContainerCodec()
        content = ExamWorkspaceContainerContent(
            document=_document(), notes=("tables_flattened: 1",)
        )
        parsed = codec.parse(content=codec.build(content=content))
        assert parsed == content

    def test_build_is_deterministic(self) -> None:
        codec = ExamWorkspaceContainerCodec()
        content = ExamWorkspaceContainerContent(document=_document())
        assert codec.build(content=content) == codec.build(content=content)

    def test_rejects_non_zip(self) -> None:
        with pytest.raises(DomainError) as exc_info:
            ExamWorkspaceContainerCodec().parse(content=b"garbage")
        assert exc_info.value.code is ErrorCode.DOCUMENT_UNREADABLE

    def test_rejects_tampered_document(self) -> None:
        codec = ExamWorkspaceContainerCodec()
        built = codec.build(content=ExamWorkspaceContainerContent(document=_document()))
        tampered = _rezip_with(built, replace={"document.json": b"{}"})
        with pytest.raises(DomainError):
            codec.parse(content=tampered)

    def test_rejects_unknown_schema_version(self) -> None:
        codec = ExamWorkspaceContainerCodec()
        built = codec.build(content=ExamWorkspaceContainerContent(document=_document()))
        manifest = json.loads(zipfile.ZipFile(io.BytesIO(built)).read("manifest.json"))
        manifest["schema_version"] = "unknown_v9"
        tampered = _rezip_with(
            built, replace={"manifest.json": json.dumps(manifest).encode("utf-8")}
        )
        with pytest.raises(DomainError):
            codec.parse(content=tampered)

    def test_rejects_stray_entries(self) -> None:
        codec = ExamWorkspaceContainerCodec()
        built = codec.build(content=ExamWorkspaceContainerContent(document=_document()))
        tampered = _rezip_with(built, replace={"evil.txt": b"nope"})
        with pytest.raises(DomainError):
            codec.parse(content=tampered)


def _container_with_document_bytes(
    document_bytes: bytes, *, document_id: str, revision: int
) -> bytes:
    manifest = {
        "schema_version": EXAM_WORKSPACE_CONTAINER_SCHEMA_VERSION,
        "document_id": document_id,
        "revision": revision,
        "document_sha256": hashlib.sha256(document_bytes).hexdigest(),
        "notes": [],
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as target:
        target.writestr("manifest.json", json.dumps(manifest).encode("utf-8"))
        target.writestr("document.json", document_bytes)
    return buffer.getvalue()


class TestStoredContentContainment:
    def test_huge_integer_in_document_is_unreadable(self) -> None:
        document = _document()
        bad_document = (
            b'{"schema_version": "native_exam_document_v10", "probe": ' + b"9" * 5000 + b"}"
        )
        content = _container_with_document_bytes(
            bad_document,
            document_id=str(document.document_id),
            revision=document.revision,
        )

        with pytest.raises(DomainError) as exc_info:
            ExamWorkspaceContainerCodec().parse(content=content)

        assert exc_info.value.code is ErrorCode.DOCUMENT_UNREADABLE

    def test_huge_integer_in_manifest_is_unreadable(self) -> None:
        codec = ExamWorkspaceContainerCodec()
        built = codec.build(content=ExamWorkspaceContainerContent(document=_document()))
        bad_manifest = b'{"probe": ' + b"9" * 5000 + b"}"
        tampered = _rezip_with(built, replace={"manifest.json": bad_manifest})

        with pytest.raises(DomainError) as exc_info:
            codec.parse(content=tampered)

        assert exc_info.value.code is ErrorCode.DOCUMENT_UNREADABLE

    def test_list_manifest_is_unreadable_with_manifest_message(self) -> None:
        codec = ExamWorkspaceContainerCodec()
        built = codec.build(content=ExamWorkspaceContainerContent(document=_document()))
        tampered = _rezip_with(built, replace={"manifest.json": b'["not", "an", "object"]'})

        with pytest.raises(DomainError) as exc_info:
            codec.parse(content=tampered)

        assert exc_info.value.code is ErrorCode.DOCUMENT_UNREADABLE
        assert exc_info.value.message == "Dokumentets manifest kunde inte läsas."

    def test_corrupt_document_member_is_unreadable(self) -> None:
        codec = ExamWorkspaceContainerCodec()
        built = codec.build(content=ExamWorkspaceContainerContent(document=_document()))
        with zipfile.ZipFile(io.BytesIO(built)) as source:
            manifest_bytes = source.read("manifest.json")
            document_bytes = source.read("document.json")
        stored = io.BytesIO()
        with zipfile.ZipFile(stored, "w", compression=zipfile.ZIP_STORED) as target:
            target.writestr("manifest.json", manifest_bytes)
            target.writestr("document.json", document_bytes)
        raw = bytearray(stored.getvalue())
        offset = raw.find(document_bytes)
        assert offset >= 0
        raw[offset + len(document_bytes) // 2] ^= 0xFF

        with pytest.raises(DomainError) as exc_info:
            codec.parse(content=bytes(raw))

        assert exc_info.value.code is ErrorCode.DOCUMENT_UNREADABLE

    def test_unknown_decode_error_is_unreadable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        class _UnexpectedDecodeError(Exception):
            pass

        def _raise_unexpected(payload: object) -> object:
            raise _UnexpectedDecodeError("injected decode failure")

        codec = ExamWorkspaceContainerCodec()
        built = codec.build(content=ExamWorkspaceContainerContent(document=_document()))
        monkeypatch.setattr(json, "loads", _raise_unexpected)

        with pytest.raises(DomainError) as exc_info:
            codec.parse(content=built)

        assert exc_info.value.code is ErrorCode.DOCUMENT_UNREADABLE

    def test_keyboard_interrupt_propagates(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def _raise_interrupted(payload: object) -> object:
            raise KeyboardInterrupt

        codec = ExamWorkspaceContainerCodec()
        built = codec.build(content=ExamWorkspaceContainerContent(document=_document()))
        monkeypatch.setattr(json, "loads", _raise_interrupted)

        with pytest.raises(KeyboardInterrupt):
            codec.parse(content=built)

    def test_outdated_document_keeps_code_and_details(self) -> None:
        document = _document()
        payload = json.loads(native_exam_document_json_bytes(document))
        payload["schema_version"] = "native_exam_document_v9"
        content = _container_with_document_bytes(
            json.dumps(payload).encode("utf-8"),
            document_id=str(document.document_id),
            revision=document.revision,
        )

        with pytest.raises(DomainError) as exc_info:
            ExamWorkspaceContainerCodec().parse(content=content)

        assert exc_info.value.code is ErrorCode.DOCUMENT_SCHEMA_OUTDATED
        assert exc_info.value.details == {"schema_version": "native_exam_document_v9"}

    def test_invalid_current_document_is_unreadable(self) -> None:
        document = _document()
        payload = json.loads(native_exam_document_json_bytes(document))
        payload["items"][0]["sequence"] = 2
        content = _container_with_document_bytes(
            json.dumps(payload).encode("utf-8"),
            document_id=str(document.document_id),
            revision=document.revision,
        )

        with pytest.raises(DomainError) as exc_info:
            ExamWorkspaceContainerCodec().parse(content=content)

        assert exc_info.value.code is ErrorCode.DOCUMENT_UNREADABLE

    def test_unreadable_maps_to_422(self) -> None:
        from skriptoteket.web.error_mapping import error_to_status

        assert error_to_status(ErrorCode.DOCUMENT_UNREADABLE) == 422
