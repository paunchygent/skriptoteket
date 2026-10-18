/**
 * Public Exam Converter view contracts.
 *
 * Domain purpose:
 *   Keep the teacher-facing target vocabulary of the public guest converter
 *   independent of the transport-specific API module.
 *
 * Relationships:
 *   - Used by the upload panel and the public runtime composable for target selection.
 *   - Mirrors the governed Sir Convert DigiExam migration target vocabulary.
 */

export type ExamConverterTarget = "examnet_pdf" | "qti_package";
