/**
 * Grouping public guest share orchestration for the planner shell.
 *
 * This composable injects grouping-specific copy and helper-route calls into
 * the browser-owned public `Dela länk` flow.
 */

import type { Ref } from "vue";

import { createPublicGroupingShare } from "./classroomPlannerPublicShareApi";
import { createClassroomPlannerPublicShareFlow } from "./classroomPlannerPublicShareFlow";
import type { ClassroomPlannerGuestSnapshot } from "./classroomPlannerGuestSnapshot";
import type { PlanDraft } from "./classroomPlannerTypes";
import type { PlannerTransitionResult } from "./plannerTransitionPolicies";

type GroupingSharePlannerState = {
  draft: PlanDraft | null | Ref<PlanDraft | null>;
  prepareForExport: (messages: {
    conflictMessage: string;
    fallbackMessage: string;
  }) => Promise<PlannerTransitionResult>;
};

type UsePublicGroupingShareFlowOptions = {
  plannerState: GroupingSharePlannerState;
  getSnapshot: () => Promise<ClassroomPlannerGuestSnapshot>;
};

export function usePublicGroupingShareFlow(options: UsePublicGroupingShareFlowOptions) {
  return createClassroomPlannerPublicShareFlow<"grouping">({
    plannerState: options.plannerState,
    getSnapshot: options.getSnapshot,
    draftKind: "grouping",
    createShare: createPublicGroupingShare,
    messages: {
      missingDraftMessage: "Öppna en gruppindelning innan du delar länken.",
      initialStatusLabel: "Skapar länk…",
      copiedMessage: "Länken är kopierad.",
      fallbackMessage: "Det gick inte att skapa länken just nu.",
    },
  });
}
