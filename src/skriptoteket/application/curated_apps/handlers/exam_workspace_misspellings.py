"""Use the document's language for teacher-keyed automatic gap values."""

from skriptoteket.application.curated_apps.exam_workspace_misspellings import (
    ExamWorkspaceMisspellingsRequest,
    ExamWorkspaceMisspellingsResponse,
)
from skriptoteket.domain.curated_apps.exam_workspace.answer_misspellings import (
    produce_answer_misspellings,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_document_language import (
    infer_exam_document_language,
)


class GenerateExamWorkspaceMisspellingsHandler:
    def handle(
        self, *, request: ExamWorkspaceMisspellingsRequest
    ) -> ExamWorkspaceMisspellingsResponse:
        return ExamWorkspaceMisspellingsResponse(
            automatic_values=produce_answer_misspellings(
                request.accepted_values,
                language=infer_exam_document_language(request.document_text),
                other_gold_answers=request.other_gold_answers,
            )
        )
