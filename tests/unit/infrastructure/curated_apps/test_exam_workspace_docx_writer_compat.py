"""The Word export must open in modern Word without Compatibility Mode.

python-docx's default template ships ``compatibilityMode`` 14, which makes Word open
the exam workspace export in Compatibility Mode (Mac staging walk of
TASK-SKRIPT-39-04-22 at 74eeceb2d, 2026-10-22). Every export must carry
``compatibilityMode`` 15 instead.
"""

import io
import zipfile
from xml.etree import ElementTree

from skriptoteket.infrastructure.curated_apps.apps.conversion_hub import (
    exam_workspace_docx_writer,
)
from tests.unit.infrastructure.curated_apps.exam_workspace_docx_writer_test_support import (
    all_kinds_document,
)

ExamWorkspaceDocxWriter = exam_workspace_docx_writer.ExamWorkspaceDocxWriter

_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_COMPAT_URI = "http://schemas.microsoft.com/office/word"


def _compatibility_mode(docx_bytes: bytes) -> str | None:
    with zipfile.ZipFile(io.BytesIO(docx_bytes)) as package:
        settings = ElementTree.fromstring(package.read("word/settings.xml"))
    for setting in settings.iter(f"{{{_W}}}compatSetting"):
        if setting.get(f"{{{_W}}}name") == "compatibilityMode":
            assert setting.get(f"{{{_W}}}uri") == _COMPAT_URI
            return setting.get(f"{{{_W}}}val")
    return None


class TestCompatibilityMode:
    def test_export_carries_compatibility_mode_15(self) -> None:
        docx_bytes = ExamWorkspaceDocxWriter().build_docx_bytes(all_kinds_document())

        assert _compatibility_mode(docx_bytes) == "15"
