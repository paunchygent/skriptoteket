"""The export route names the download after the file the handler produced (D1).

Swedish letters are not ASCII, so the header carries the RFC 5987 form.
"""

from __future__ import annotations

from urllib.parse import unquote
from uuid import UUID, uuid4

import pytest

from skriptoteket.application.curated_apps.exam_workspace import (
    ExamWorkspaceExportChecklistResponse,
    ExamWorkspaceExportFile,
    ExamWorkspaceExportTarget,
)
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.vault import VaultFile
from skriptoteket.web.api.v1 import apps_conversion_hub_exam_workspace_exports as api
from tests.fixtures.identity_fixtures import make_user
from tests.unit.web.test_apps_exam_workspace_answer_key_suggestions_api import FakeRegistry

pytestmark = pytest.mark.unit


class FixedFileHandler:
    def __init__(self, filename: str) -> None:
        self.filename = filename

    async def handle(
        self,
        *,
        actor: User,
        lineage_id: UUID,
        target: ExamWorkspaceExportTarget,
        expected_revision: int,
    ) -> ExamWorkspaceExportFile:
        return ExamWorkspaceExportFile(
            filename=self.filename, media_type="application/pdf", content=b"%PDF"
        )

    async def save(
        self,
        *,
        actor: User,
        lineage_id: UUID,
        target: ExamWorkspaceExportTarget,
        expected_revision: int,
    ) -> VaultFile:
        raise AssertionError("the download route must not save")

    async def checklist(
        self, *, actor: User, lineage_id: UUID, expected_revision: int
    ) -> ExamWorkspaceExportChecklistResponse:
        raise AssertionError("the download route must not build a checklist")


async def _download(filename: str):
    return await api.export_exam_workspace_document(
        lineage_id=uuid4(),
        target=ExamWorkspaceExportTarget.PDF,
        expected_revision=1,
        registry=FakeRegistry(),
        handler=FixedFileHandler(filename),
        user=make_user(),
    )


@pytest.mark.asyncio
async def test_swedish_title_file_name_is_sent_as_a_utf8_header() -> None:
    response = await _download("Läsförståelse åk 7.pdf")

    header = response.headers["content-disposition"]
    assert header.startswith("attachment; filename*=utf-8''")
    assert unquote(header.split("''", 1)[1]) == "Läsförståelse åk 7.pdf"


@pytest.mark.asyncio
async def test_ascii_title_file_name_stays_a_plain_attachment() -> None:
    response = await _download("Prov 1.pdf")

    assert response.headers["content-disposition"] == 'attachment; filename="Prov 1.pdf"'
