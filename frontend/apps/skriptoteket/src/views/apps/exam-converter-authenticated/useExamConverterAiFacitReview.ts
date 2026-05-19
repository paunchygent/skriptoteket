/**
 * Exam Converter AI-facit review action types.
 *
 * Domain purpose:
 *   Name the focused review affordance for advisory AI answer-key suggestions
 *   while the actual teacher save path stays in the item facit editor.
 *
 * Relationships:
 *   - Used by the workspace and question review shell for navigation focus.
 *   - Does not store local answer-key decisions or build correction intents.
 */

export type ExamConverterAiFacitReviewAction = "review" | "accept" | "edit";
