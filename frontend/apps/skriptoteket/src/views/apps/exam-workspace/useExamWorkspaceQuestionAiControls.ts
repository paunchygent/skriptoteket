/**
 * Exam workspace per-question AI controls, computed once per question.
 *
 * Domain purpose:
 *   Hold the one computed state the two surfaces of a question's AI controls
 *   read (TASK-SKRIPT-40-04-26 D7): the question-text toolbar's AI group and
 *   the ⋮ Fler åtgärder menu rows on a phone or touch device. Both show the
 *   same three controls in the same states, so the question is asked for its
 *   suggestion through one place, never two.
 *
 *   The rules themselves live in `questionAiControls`; this composable only
 *   supplies the workspace state they read: the provided single-question AI
 *   harness (`examWorkspaceQuestionAiKeys`), the guest mode
 *   (`useExamWorkspaceAiMode`) and the door's daily limit under the `small`
 *   allowance, the same note the header shows.
 *
 * Relationships:
 *   - Called by `ExamWorkspaceQuestionEditor`, which passes `controls` to
 *     `ExamWorkspaceQuestionAiGroup` and to `ExamWorkspaceQuestionHead` and
 *     routes both surfaces' suggest intent to `suggest`.
 *   - Without a provided AI harness the controls carry no suggest control, so
 *     no surface can ask for a suggestion the workspace cannot run.
 */

import { computed } from "vue";
import type { ComputedRef } from "vue";

import type { NativeExamItem } from "../../../api/examWorkspace";
import { aiDailyLimitFor } from "../../../composables/aiDailyLimit";
import { questionAiControls } from "./examWorkspaceQuestionAi";
import type { QuestionAiControls } from "./examWorkspaceQuestionAi";
import { useExamWorkspaceQuestionAi } from "./examWorkspaceQuestionAiKeys";
import { useExamWorkspaceAiMode } from "./useExamWorkspaceAiMode";

/** The one question state both of its AI surfaces read, plus its one suggest request. */
export type ExamWorkspaceQuestionAiControls = {
  /** The three controls this question shows, each null when not shown. */
  controls: ComputedRef<QuestionAiControls>;
  /** Ask the workspace for this question's one answer-key suggestion. */
  suggest: () => void;
};

/**
 * Compute the question's AI controls from its own state and the workspace's.
 *
 * `locked` is the question's whole lock: disabled, still converting, or any
 * later reason the owner adds.
 */
export function useExamWorkspaceQuestionAiControls(
  item: () => NativeExamItem,
  locked: () => boolean,
): ExamWorkspaceQuestionAiControls {
  const keys = useExamWorkspaceQuestionAi();
  const aiMode = useExamWorkspaceAiMode();
  /** The door's daily limit, under the allowance every exam-workspace AI action marks. */
  const { note: aiDailyLimitNote } = aiDailyLimitFor("small");

  const controls = computed(() =>
    questionAiControls(item(), {
      busy: keys?.busy.value ?? false,
      guest: aiMode.value === "guest",
      limitNote: aiDailyLimitNote.value,
      locked: locked(),
      suggestAvailable: keys !== null,
    }),
  );

  function suggest(): void {
    keys?.suggest(item().item_id);
  }

  return { controls, suggest };
}
