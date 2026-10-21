"""Untitled exam file names for saved native exams (TASK-SKRIPT-40-04-21 D11).

Purpose:
    Name a saved exam container whose document title is empty: the Mina filer
    file name and the Prov list label fall back to "Namnlöst prov" while the
    document title itself stays empty until the teacher sets it in Uppgifter.

Relationships:
    - Thin wrapper over ``domain.scripting.vault_names.rename_vault_filename``,
      which owns the stem-only rename rules; this module owns only the exam
      fallback name and the exam-owned extension.
    - Used by ``CreateBlankExamWorkspaceDocumentHandler`` and the guest sign-in
      draft handoff (``exam_workspace_guest_draft_handoff``) so both lanes name
      an untitled exam identically.
"""

from __future__ import annotations

from skriptoteket.domain.scripting.vault_names import rename_vault_filename

EXAM_DOCUMENT_FILE_EXTENSION = ".provdokument.zip"
UNTITLED_EXAM_NAME = "Namnlöst prov"


def exam_document_file_name(title: str) -> str:
    """Return the Mina filer file name for an exam title, falling back when empty."""
    return rename_vault_filename(
        stem=title.strip() or UNTITLED_EXAM_NAME, extension=EXAM_DOCUMENT_FILE_EXTENSION
    )
