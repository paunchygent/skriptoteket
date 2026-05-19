/**
 * Exam Converter AI prefill focus types.
 *
 * Domain purpose:
 *   Name the focus state for advisory AI answer-key candidates that seed the
 *   normal item facit editor.
 *
 * Relationships:
 *   - Used by the workspace and question review shell for navigation focus.
 *   - Does not store local answer-key decisions or build correction intents.
 */

export type ExamConverterAiPrefillFocus = "candidate" | "questions";
