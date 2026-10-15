"""Student shared stems retain positioned pictures without exposing facit assets."""

import hashlib
import posixpath
import zipfile
from io import BytesIO
from uuid import uuid4
from xml.etree import ElementTree

import pytest
from PIL import Image

from skriptoteket.application.curated_apps.handlers.exam_workspace_exports import (
    build_native_examnet_qti_package,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeAnswerKey,
    NativeAnswerKeyOrigin,
    NativeAssetSegment,
    NativeExamAsset,
    NativeExamDocument,
    NativeExamDocumentOrigin,
    NativeExamItem,
    NativeExamItemKind,
    NativeExamParent,
    NativeItemReview,
    NativeItemReviewState,
    NativeParagraph,
    NativeParseOrigin,
    NativeTextSegment,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_qti_writer import (
    ExamNetQtiPackageWriter,
)


def _png() -> bytes:
    buffer = BytesIO()
    Image.new("RGBA", (8, 4), (25, 130, 60, 180)).save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.mark.parametrize("child_count,global_stem", [(1, False), (2, False), (1, True)])
def test_shared_picture_is_positioned_once_and_child_resources_stay_bound(
    child_count: int,
    global_stem: bool,
) -> None:
    payload = _png()
    digest = hashlib.sha256(payload).hexdigest()
    asset_id = f"asset_{digest[:16]}"
    stem = (
        NativeParagraph(
            segments=(
                NativeTextSegment(text="Betrakta: "),
                NativeAssetSegment(asset_id=asset_id),
                NativeTextSegment(text=" diagrammet."),
            )
        ),
    )
    items = tuple(
        NativeExamItem(
            item_id=f"item_{index:03d}",
            sequence=index,
            kind=NativeExamItemKind.FREE_TEXT,
            body=(
                NativeParagraph(
                    segments=(
                        NativeTextSegment(text=f"Fråga {index}: "),
                        NativeAssetSegment(asset_id=asset_id),
                    )
                ),
            ),
            points=1,
            answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
            review=NativeItemReview(
                state=NativeItemReviewState.REVIEW_COMPLETE,
                parse_origin=NativeParseOrigin.LLM_PARSED,
            ),
        )
        for index in range(1, child_count + 1)
    )
    parents = (
        ()
        if global_stem
        else (
            NativeExamParent(
                parent_id="parent_001",
                instruction=stem,
                item_ids=tuple(item.item_id for item in items),
            ),
        )
    )
    document = NativeExamDocument(
        document_id=uuid4(),
        revision=1,
        title="Diagramprov",
        items=items,
        parents=parents,
        instructions=stem if global_stem else (),
        assets=(
            NativeExamAsset(
                asset_id=asset_id,
                media_type="image/png",
                byte_length=len(payload),
                sha256=digest,
            ),
        ),
        origin=NativeExamDocumentOrigin(kind="created"),
    )
    package, _report = build_native_examnet_qti_package(
        document,
        package_name="diagramprov",
        qti_writer=ExamNetQtiPackageWriter(),
        assets_by_id={asset_id: payload},
    )
    with zipfile.ZipFile(BytesIO(package)) as archive:
        item_path = next(
            name
            for name in archive.namelist()
            if name.startswith("items/") and name.endswith(".xml")
        )
        root = ElementTree.fromstring(archive.read(item_path))
        images = [node for node in root.iter() if node.tag.rsplit("}", 1)[-1] == "img"]
        assert len(images) == child_count + 1
        stem_picture = images[0]
        paragraph = next(node for node in root.iter() if stem_picture in list(node))
        assert paragraph.text == "Betrakta: "
        assert stem_picture.tail == " diagrammet."
        assert "".join(root.itertext()).count("Betrakta:") == 1
        for image in images:
            target = posixpath.normpath(
                posixpath.join(posixpath.dirname(item_path), image.attrib["src"])
            )
            assert archive.read(target) == payload
            with Image.open(BytesIO(archive.read(target))) as actual:
                actual.verify()
