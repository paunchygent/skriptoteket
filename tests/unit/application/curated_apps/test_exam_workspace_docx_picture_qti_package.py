"""D2: positioned converted pictures reach real Exam.net XML and ZIP resources.

Converter output is controlled fixture input; native projection, assembly and the
QTI package writer are real. This is package proof, not an Exam.net import.
"""

import base64
import hashlib
import zipfile
from io import BytesIO
from pathlib import PurePosixPath
from uuid import uuid4
from xml.etree import ElementTree

import pytest
from PIL import Image

from skriptoteket.application.curated_apps.exam_workspace_exports import (
    build_native_examnet_qti_package,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_build import (
    assemble_build_result,
    native_item,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import ProducedItem
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk, DocxImage
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeAssetSegment,
    NativeExamParent,
    NativeItemReviewState,
    NativeParagraph,
    NativeParseOrigin,
    NativeTextSegment,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_qti_writer import (
    ExamNetQtiPackageWriter,
)

_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAgAAAAECAIAAAA8r+mnAAAAFElEQVR4nGOUbLJhwAaYsIqSJQEAVB8A33yzxnAAAAAASUVORK5CYII="
)


@pytest.mark.parametrize(
    "kind,picture_only,parent_instruction",
    [
        ("free_text", False, False),
        ("gap_fill", False, False),
        ("free_text", True, False),
        ("free_text", False, True),
    ],
)
def test_a_converted_picture_keeps_its_position_and_packaged_resource(
    kind: str, picture_only: bool, parent_instruction: bool
) -> None:
    image = DocxImage(
        _PNG,
        "image/png",
        offset=0 if picture_only else 10,
        marked_offset=0 if picture_only else 10,
        width=8,
        height=4,
    )
    text = "" if picture_only else "Beskriv:  bilden."
    chunk = DocxChunk("body:0001", "drawing" if picture_only else "paragraph", text, text, (image,))
    asset: dict[str, object] = {
        "kind": "asset",
        "text": None,
        "accepted_values": [],
        "asset_id": image.asset_id,
    }
    segments: list[dict[str, object]] = (
        [asset]
        if picture_only
        else [
            {"kind": "text", "text": "Beskriv:  ", "accepted_values": [], "asset_id": None},
            asset,
            {"kind": "text", "text": "bilden.", "accepted_values": [], "asset_id": None},
        ]
    )
    if kind == "gap_fill":
        segments.append(
            {"kind": "gap", "text": None, "accepted_values": ["symbol"], "asset_id": None}
        )
    produced = ProducedItem.model_validate(
        {
            "source_anchors": [chunk.anchor],
            "outcome": "converted",
            "conflict_kind": None,
            "review_reason": None,
            "kind": kind,
            "printed_label": "Fråga 1",
            "body": [{"segments": segments}],
            "points": 1,
            "choices": [],
            "marking_guide": None,
        }
    )
    converted = native_item(produced, chunks=(chunk,))
    assert converted.review.parse_origin is NativeParseOrigin.LLM_PARSED
    assert converted.review.state is NativeItemReviewState.REVIEW_COMPLETE
    assert isinstance(converted.body[0].segments[0 if picture_only else 1], NativeAssetSegment)
    built = assemble_build_result(
        document_id=uuid4(),
        filename="bildprov.docx",
        source_sha256=hashlib.sha256(b"source").hexdigest(),
        chunks=(chunk,),
        accepted=((converted, (chunk.anchor,)),),
        review_reasons={},
    )
    document = built.document
    if parent_instruction:
        document = document.model_copy(
            update={
                "parents": (
                    NativeExamParent(
                        parent_id="parent_001",
                        instruction=(
                            NativeParagraph(
                                segments=(NativeTextSegment(text="Gemensam instruktion."),)
                            ),
                        ),
                        item_ids=(document.items[0].item_id,),
                    ),
                )
            }
        )
    package, _report = build_native_examnet_qti_package(
        document,
        package_name="bildprov",
        qti_writer=ExamNetQtiPackageWriter(),
        assets_by_id=built.assets_by_id,
    )
    with zipfile.ZipFile(BytesIO(package)) as archive:
        item_path = next(
            name
            for name in archive.namelist()
            if name.startswith("items/") and name.endswith(".xml")
        )
        root = ElementTree.fromstring(archive.read(item_path))
        if parent_instruction:
            rendered = "".join(root.itertext())
            assert rendered.index("Gemensam instruktion.") < rendered.index("Beskriv:")
        images = [element for element in root.iter() if element.tag.rsplit("}", 1)[-1] == "img"]
        assert len(images) == 1
        picture_parent = next(parent for parent in root.iter() if images[0] in list(parent))
        assert picture_parent.tag.rsplit("}", 1)[-1] in {"prompt", "p"}
        if picture_only:
            assert not any(text.strip() for text in picture_parent.itertext())
        else:
            assert picture_parent.text == "Beskriv:  "
            assert images[0].tail == "bilden."
        if kind == "gap_fill":
            assert [child.tag.rsplit("}", 1)[-1] for child in picture_parent] == [
                "img",
                "textEntryInteraction",
            ]
        relative = PurePosixPath(item_path).parent / images[0].attrib["src"]
        parts: list[str] = []
        for part in relative.parts:
            if part == "..":
                parts.pop()
            elif part != ".":
                parts.append(part)
        image_path = "/".join(parts)
        assert archive.read(image_path) == _PNG
        with Image.open(BytesIO(archive.read(image_path))) as picture:
            assert picture.size == (8, 4)
            picture.verify()
        manifest = ElementTree.fromstring(archive.read("imsmanifest.xml"))
        assert any(
            any(
                child.tag.rsplit("}", 1)[-1] == "file" and child.get("href") == image_path
                for child in resource
            )
            for resource in manifest.iter()
            if resource.tag.rsplit("}", 1)[-1] == "resource"
        ), "The picture must be declared under a packaged QTI resource"
