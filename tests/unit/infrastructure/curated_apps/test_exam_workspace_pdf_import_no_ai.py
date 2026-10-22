"""The PDF import modules add no AI call site and open no new import lane."""

import ast
from pathlib import Path

import pytest

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeySourceKind,
)
from tests.unit.application.curated_apps.handlers.test_exam_workspace_documents import (
    _actor,
)
from tests.unit.application.curated_apps.handlers.test_exam_workspace_import_course import (
    importer,
)

PDF_MODULES = (
    "src/skriptoteket/domain/curated_apps/exam_workspace/import_file_format.py",
    "src/skriptoteket/infrastructure/curated_apps/apps/conversion_hub/exam_workspace_import_source.py",  # noqa: E501
    "src/skriptoteket/infrastructure/curated_apps/apps/conversion_hub/exam_workspace_pdf_chunker.py",  # noqa: E501
    "src/skriptoteket/infrastructure/curated_apps/apps/conversion_hub/exam_workspace_pdf_blocks.py",  # noqa: E501
    "src/skriptoteket/infrastructure/curated_apps/apps/conversion_hub/exam_workspace_pdf_layout.py",  # noqa: E501
    "src/skriptoteket/infrastructure/curated_apps/apps/conversion_hub/exam_workspace_pdf_graphics.py",  # noqa: E501
    "src/skriptoteket/infrastructure/curated_apps/apps/conversion_hub/exam_workspace_pdf_pictures.py",  # noqa: E501
    "src/skriptoteket/infrastructure/documents/pdfium_access.py",
)

FORBIDDEN_IMPORT_PREFIXES = (
    "httpx",
    "openai",
    "anthropic",
    "skriptoteket.infrastructure.llm",
    "skriptoteket.protocols.item_type_labeler",
    "skriptoteket.protocols.exam_grouping",
    "skriptoteket.protocols.llm",
    "skriptoteket.application",
)


def _imported_module_names(path: Path) -> set[str]:
    """Every imported module name, including imports inside functions."""
    tree = ast.parse(path.read_text(), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.add(node.module)
    return names


@pytest.mark.parametrize("module", PDF_MODULES)
def test_pdf_module_imports_no_ai_call_site(module):
    imported = _imported_module_names(Path(module))
    offenders = sorted(name for name in imported if name.startswith(FORBIDDEN_IMPORT_PREFIXES))
    assert offenders == [], f"{module} imports an AI call site: {offenders}"


@pytest.mark.asyncio
async def test_pdf_job_uses_the_word_source_kind():
    """The PDF import queues the same DOCX_IMPORT lane as a Word import: no new lane."""
    word_handler, word_jobs, _ = importer()
    pdf_handler, pdf_jobs, _ = importer()
    word_status = await word_handler.handle(
        actor=_actor(), filename="prov.docx", content=b"queued DOCX source", course_key=None
    )
    pdf_status = await pdf_handler.handle(
        actor=_actor(), filename="prov.pdf", content=b"%PDF-1.4 fake", course_key=None
    )
    assert word_status.state == "queued"
    assert pdf_status.state == "queued"
    word_job = word_jobs.jobs[word_status.job_id]
    pdf_job = pdf_jobs.jobs[pdf_status.job_id]
    assert pdf_job.source_kind is word_job.source_kind is ExamAnswerKeySourceKind.DOCX_IMPORT
