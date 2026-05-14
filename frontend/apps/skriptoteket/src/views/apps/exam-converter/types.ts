/**
 * Shared Exam Converter view contracts.
 *
 * Domain purpose:
 *   Keep the teacher-facing target vocabulary shared between public and
 *   authenticated Exam Converter views without coupling either view to a
 *   transport-specific API module.
 *
 * Relationships:
 *   - Used by upload panels and runtime composables for target selection.
 *   - Mirrors the governed Sir Convert DigiExam migration target vocabulary.
 */

export type ExamConverterTarget = "examnet_pdf" | "qti_package";
