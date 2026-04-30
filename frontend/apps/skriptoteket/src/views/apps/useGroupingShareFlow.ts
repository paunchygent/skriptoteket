/**
 * Grouping share-link orchestration for the planner route shell.
 *
 * This composable injects grouping-specific authenticated share endpoints into
 * the shared share-link state machine so grouping can add Dela länk without
 * coupling the toolbar to raw API paths.
 */

import {
  createGroupingShare,
  listGroupingShares,
  revokeClassroomPlannerShare,
} from "./classroomPlannerShareApi";
import { createClassroomPlannerShareFlow } from "./classroomPlannerShareFlow";
import type { PlanDraft } from "./classroomPlannerTypes";
import type { PlannerTransitionResult } from "./plannerTransitionPolicies";

type GroupingSharePlannerState = {
  draft: PlanDraft | null;
  prepareForExport: (messages: {
    conflictMessage: string;
    fallbackMessage: string;
  }) => Promise<PlannerTransitionResult>;
};

type UseGroupingShareFlowOptions = {
  plannerState: GroupingSharePlannerState;
};

export function useGroupingShareFlow(options: UseGroupingShareFlowOptions) {
  return createClassroomPlannerShareFlow({
    plannerState: options.plannerState,
    draftKind: "grouping",
    createShare: createGroupingShare,
    listShares: listGroupingShares,
    revokeShare: revokeClassroomPlannerShare,
    messages: {
      missingDraftMessage: "Öppna en gruppindelning innan du delar länken.",
      scopeChangedMessage: "Grouping share scope changed.",
      initialStatusLabel: "Skapar delningslänk…",
      copiedMessage: "Delningslänken är kopierad.",
      createFallbackMessage: "Det gick inte att skapa delningslänken just nu.",
      listFallbackMessage: "Kunde inte hämta delade länkar.",
      revokeFallbackMessage: "Kunde inte återkalla länken just nu.",
      copyUnavailableMessage: "Länken kan inte kopieras förrän den skapats om.",
    },
  });
}
