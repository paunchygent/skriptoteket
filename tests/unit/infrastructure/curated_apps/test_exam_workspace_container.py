"""Unit tests for the exam workspace container codec (fail-closed parsing)."""

import io
import json
import zipfile
from uuid import uuid4

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.container import (
    ExamWorkspaceContainerContent,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeAnswerKey,
    NativeAnswerKeyOrigin,
    NativeExamDocument,
    NativeExamDocumentOrigin,
    NativeExamItem,
    NativeExamItemKind,
    NativeItemReview,
    NativeItemReviewState,
    NativeParagraph,
    NativeParseOrigin,
    NativeTextSegment,
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
                body=(NativeParagraph(segments=(NativeTextSegment(text="Resonera om stil."),)),),
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
        assert exc_info.value.code is ErrorCode.VALIDATION_ERROR

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
