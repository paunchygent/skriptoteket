/**
 * Classroom planner smart-run action adapter.
 *
 * Purpose:
 *   Route shuffle button requests to either local randomization or Smart
 *   seating/grouping execution based on the active draft flags.
 *
 * Relationships:
 *   - consumed by `useClassroomState.ts`
 *   - keeps run-button orchestration separate from planner state composition
 */

import type { Ref } from "vue";

import { isSmartEnabledByDefault } from "./classroomPlannerSmartDefaults";
import type { PlanDraft } from "./classroomPlannerTypes";

type SmartRun = {
  clearFeedback: () => void;
  run: () => Promise<unknown>;
};

type CreateClassroomPlannerSmartRunActionsOptions = {
  draft: Ref<PlanDraft | null>;
  smartSeatingRun: SmartRun;
  smartGroupingRun: SmartRun;
  randomizeSeating: () => void;
  randomizeGroups: () => void;
  clearFeedbackBeforeRun?: boolean;
};

export function createClassroomPlannerSmartRunActions(
  options: CreateClassroomPlannerSmartRunActionsOptions,
) {
  async function runSeatingShuffle(): Promise<void> {
    if (options.clearFeedbackBeforeRun) {
      options.smartSeatingRun.clearFeedback();
    }
    if (!options.draft.value || options.draft.value.draft_kind !== "seating") {
      return;
    }
    if (!isSmartEnabledByDefault(options.draft.value)) {
      options.smartSeatingRun.clearFeedback();
      options.randomizeSeating();
      return;
    }
    await options.smartSeatingRun.run();
  }

  async function runGroupingShuffle(): Promise<void> {
    if (options.clearFeedbackBeforeRun) {
      options.smartGroupingRun.clearFeedback();
    }
    if (!options.draft.value || options.draft.value.draft_kind !== "grouping") {
      return;
    }
    if (!isSmartEnabledByDefault(options.draft.value)) {
      options.smartGroupingRun.clearFeedback();
      options.randomizeGroups();
      return;
    }
    await options.smartGroupingRun.run();
  }

  return {
    runSeatingShuffle,
    runGroupingShuffle,
  };
}
