/**
 * Exam workspace editor keys.
 *
 * Domain purpose:
 *   Provide, once, the two injection harnesses every question editor below
 *   the workspace reads. The first is the workspace's Ångra and Gör om as
 *   Ctrl/Cmd+Z reaches them from inside an exam text editor
 *   (TASK-SKRIPT-40-04-06 D2), so a gap or picture record returns with the
 *   text. The second is the single-question AI harness the question-text
 *   toolbar's AI group asks for and reads (TASK-SKRIPT-40-04-26 D3). Both
 *   answer what an editor may do rather than how it draws, and the workspace
 *   provides both at the same point from the same values, so one owner keeps
 *   the pair together and its busy value derived once.
 *
 * Relationships:
 *   - `examWorkspaceHistoryKeys` owns the Ångra/Gör om key; this passes the
 *     autosave history's own undo, redo and availability, so the top-bar pair
 *     and the editor pair disable on one value.
 *   - `examWorkspaceQuestionAiKeys` owns the AI key; this passes the same
 *     `item_id` request and the busy value the header's suggest-all disables
 *     on, so the toolbar computes no second availability.
 *   - `ExamWorkspaceView` calls it once with `useExamWorkspaceEnrichment` and
 *     the editing history, and hands the returned busy value to the header,
 *     the export menu and the drawers.
 */

import { computed } from "vue";
import type { Ref } from "vue";

import { provideExamWorkspaceHistoryKeys } from "./examWorkspaceHistoryKeys";
import { provideExamWorkspaceQuestionAi } from "./examWorkspaceQuestionAiKeys";

/** The workspace values the editor keys expose, each already owned elsewhere. */
export type ExamWorkspaceEditorKeySources = {
  /** The autosave history the workspace's Ångra and Gör om run. */
  history: {
    undo(): Promise<void> | void;
    redo(): Promise<void> | void;
    canUndo: Readonly<Ref<boolean>>;
    canRedo: Readonly<Ref<boolean>>;
  };
  /** Answer-key enrichment: whether a suggestion runs, and the one-question request. */
  enrichment: {
    isRequesting: Readonly<Ref<boolean>>;
    isEnrichmentPending: Readonly<Ref<boolean>>;
    requestSuggestionForItem(itemId: string): Promise<void> | void;
  };
};

/**
 * Provide Ångra/Gör om and the single-question AI harness to every question
 * below the caller, and return the busy value the AI harness reads.
 */
export function useExamWorkspaceEditorKeys({ enrichment, history }: ExamWorkspaceEditorKeySources) {
  // Ctrl/Cmd+Z inside an exam text editor is the same Ångra / Gör om the buttons run.
  provideExamWorkspaceHistoryKeys({
    undo: () => void history.undo(),
    redo: () => void history.redo(),
    canUndo: history.canUndo,
    canRedo: history.canRedo,
  });
  /** The same value the header's suggest-all disables on, read by the toolbar's AI group too. */
  const enrichmentBusy = computed(() => enrichment.isRequesting.value || enrichment.isEnrichmentPending.value);
  // One question's Föreslå facit in the toolbar runs the existing `item_id` request.
  provideExamWorkspaceQuestionAi({
    busy: enrichmentBusy,
    suggest: (itemId) => void enrichment.requestSuggestionForItem(itemId),
  });
  return { enrichmentBusy };
}
