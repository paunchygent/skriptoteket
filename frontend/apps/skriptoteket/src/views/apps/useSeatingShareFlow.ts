/**
 * Seating share-link orchestration for the planner route shell.
 *
 * This composable injects seating-specific authenticated share endpoints into
 * the shared share-link state machine so seating can add Dela länk beside its
 * PDF and Excel export actions.
 */

import {
  createSeatingShare,
  listSeatingShares,
  revokeClassroomPlannerShare,
} from "./classroomPlannerShareApi";
import { createClassroomPlannerShareFlow } from "./classroomPlannerShareFlow";
import type { PlanDraft } from "./classroomPlannerTypes";
import type { PlannerTransitionResult } from "./plannerTransitionPolicies";

type SeatingSharePlannerState = {
  draft: PlanDraft | null;
  prepareForExport: (messages: {
    conflictMessage: string;
    fallbackMessage: string;
  }) => Promise<PlannerTransitionResult>;
};

type UseSeatingShareFlowOptions = {
  plannerState: SeatingSharePlannerState;
};

export function useSeatingShareFlow(options: UseSeatingShareFlowOptions) {
  return createClassroomPlannerShareFlow({
    plannerState: options.plannerState,
    draftKind: "seating",
    createShare: createSeatingShare,
    listShares: listSeatingShares,
    revokeShare: revokeClassroomPlannerShare,
    messages: {
      missingDraftMessage: "Öppna ett sittschema innan du delar länken.",
      scopeChangedMessage: "Seating share scope changed.",
      initialStatusLabel: "Skapar delningslänk…",
      copiedMessage: "Delningslänken är kopierad.",
      createFallbackMessage: "Det gick inte att skapa delningslänken just nu.",
      listFallbackMessage: "Kunde inte hämta delade länkar.",
      revokeFallbackMessage: "Kunde inte återkalla länken just nu.",
      copyUnavailableMessage: "Länken kan inte kopieras förrän den skapats om.",
    },
  });
}
