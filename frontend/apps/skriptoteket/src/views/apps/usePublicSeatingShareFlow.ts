/**
 * Seating public guest share orchestration for the planner shell.
 *
 * This composable injects seating-specific copy and helper-route calls into
 * the browser-owned public `Dela länk` flow.
 */

import type { Ref } from "vue";

import {
  createPublicSeatingShare,
  revokePublicGuestShare,
} from "./classroomPlannerPublicShareApi";
import { createClassroomPlannerPublicShareFlow } from "./classroomPlannerPublicShareFlow";
import type { ClassroomPlannerGuestSnapshot } from "./classroomPlannerGuestSnapshot";
import type { PlanDraft } from "./classroomPlannerTypes";
import type { PlannerTransitionResult } from "./plannerTransitionPolicies";

type SeatingSharePlannerState = {
  draft: PlanDraft | null | Ref<PlanDraft | null>;
  prepareForExport: (messages: {
    conflictMessage: string;
    fallbackMessage: string;
  }) => Promise<PlannerTransitionResult>;
};

type UsePublicSeatingShareFlowOptions = {
  plannerState: SeatingSharePlannerState;
  getSnapshot: () => Promise<ClassroomPlannerGuestSnapshot>;
};

export function usePublicSeatingShareFlow(options: UsePublicSeatingShareFlowOptions) {
  return createClassroomPlannerPublicShareFlow<"seating">({
    plannerState: options.plannerState,
    getSnapshot: options.getSnapshot,
    draftKind: "seating",
    createShare: createPublicSeatingShare,
    revokeShare: revokePublicGuestShare,
    messages: {
      missingDraftMessage: "Öppna ett sittschema innan du delar länken.",
      initialStatusLabel: "Skapar länk…",
      copiedMessage: "Länken är kopierad.",
      revokedMessage: "Länken är återkallad.",
      fallbackMessage: "Det gick inte att skapa delningslänken. Klicka på Skapa länk igen.",
      revokeFallbackMessage: "Det gick inte att återkalla länken. Klicka på Återkalla igen.",
    },
  });
}
