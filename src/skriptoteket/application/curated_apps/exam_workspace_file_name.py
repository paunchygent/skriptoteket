"""Exam-owned Mina filer file names that follow the exam title (TASK-SKRIPT-40-04-21 D13).

Purpose:
    Name a saved exam container after the exam title on every write: the Mina
    filer file name follows the title, and an exam whose title has no letter or
    digit falls back to "Namnlöst prov" while the document title itself stays
    as the teacher set it.

Relationships:
    - Reuses ``export_file_base_name`` from ``exam_workspace_exports``, which
      owns the title-to-stem rule, and ``title_has_text`` from
      ``domain.curated_apps.exam_workspace.native_exam_export_rules`` for the
      fallback boundary.
    - Used by ``CreateBlankExamWorkspaceDocumentHandler`` and the guest sign-in
      draft handoff (``exam_workspace_guest_draft_handoff``) for the creation
      name, and by ``ExamWorkspaceDocumentStore`` to rename the head file when
      a stored document's title differs from the indexed title.
"""

from __future__ import annotations

from skriptoteket.application.curated_apps.exam_workspace_exports import export_file_base_name
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_export_rules import (
    title_has_text,
)
from skriptoteket.domain.scripting.vault_names import rename_vault_filename

EXAM_DOCUMENT_FILE_EXTENSION = ".provdokument.zip"
UNTITLED_EXAM_NAME = "Namnlöst prov"


def exam_document_file_name(document: NativeExamDocument) -> str:
    """Return the Mina filer file name for an exam document, falling back when untitled."""
    stem = export_file_base_name(document) if title_has_text(document.title) else UNTITLED_EXAM_NAME
    return rename_vault_filename(stem=stem, extension=EXAM_DOCUMENT_FILE_EXTENSION)
