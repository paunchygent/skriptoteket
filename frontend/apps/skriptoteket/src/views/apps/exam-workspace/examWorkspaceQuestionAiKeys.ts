/**
 * Exam workspace question AI keys.
 *
 * Domain purpose:
 *   The workspace's AI harness for one question, as the question-text
 *   toolbar's AI group reaches it: whether a single-question answer-key
 *   suggestion is running, and the request itself for one question id
 *   (TASK-SKRIPT-40-04-26 D3). The workspace view provides the pair once;
 *   every question's toolbar group and ⋮ rows call it, so each Föreslå facit
 *   runs through the same `item_id` request the header's suggest-all uses.
 *
 * Relationships:
 *   - `useExamWorkspaceQuestionAiControls` injects the pair; without a
 *     provider no suggest control shows, because no workspace can ask for a
 *     suggestion there.
 *   - `ExamWorkspaceView` provides the pair from `useExamWorkspaceEnrichment`:
 *     `busy` is the same value the header's suggest-all disables on, and
 *     `suggest` is `requestSuggestionForItem`, so the toolbar computes no
 *     second availability and opens no new endpoint.
 */

import { inject, provide } from "vue";
import type { InjectionKey, Ref } from "vue";

export type ExamWorkspaceQuestionAi = {
  /** Whether an answer-key suggestion is being requested or runs. */
  busy: Readonly<Ref<boolean>>;
  /** Request one answer-key suggestion for the named question. */
  suggest(itemId: string): void;
};

const QUESTION_AI_KEYS: InjectionKey<ExamWorkspaceQuestionAi> = Symbol("exam-workspace-question-ai-keys");

/** Provide the workspace's single-question AI harness to every question below the caller. */
export function provideExamWorkspaceQuestionAi(keys: ExamWorkspaceQuestionAi): void {
  provide(QUESTION_AI_KEYS, keys);
}

/** The provided single-question AI harness, or null when no workspace provides one. */
export function useExamWorkspaceQuestionAi(): ExamWorkspaceQuestionAi | null {
  return inject(QUESTION_AI_KEYS, null);
}
