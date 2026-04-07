/**
 * Seating public export orchestration for the guest planner shell.
 *
 * This composable injects seating-specific copy and API helpers into the
 * guest direct-download export flow so public seating exports stay outside the
 * authenticated export-job/Vault boundary.
 */

import type { Ref } from "vue";

import { createClassroomPlannerPublicExportFlow } from "./classroomPlannerPublicExportFlow";
import { exportPublicSeatingSnapshot } from "./classroomPlannerPublicExportApi";
import type { GuestSnapshotMutationRunner } from "./classroomPlannerGuestDraftPersistence";
import type { ClassroomPlannerGuestSnapshot } from "./classroomPlannerGuestSnapshot";
import type { SeatingExportOption } from "./classroomPlannerExportApi";
import type { PlanDraft } from "./classroomPlannerTypes";
import type { PlannerTransitionResult } from "./plannerTransitionPolicies";

type SeatingExportPlannerState = {
  draft: PlanDraft | null | Ref<PlanDraft | null>;
  prepareForExport: (messages: {
    conflictMessage: string;
    fallbackMessage: string;
  }) => Promise<PlannerTransitionResult>;
};

type UsePublicSeatingExportFlowOptions = {
  plannerState: SeatingExportPlannerState;
  getSnapshot: () => Promise<ClassroomPlannerGuestSnapshot>;
  persistSnapshotMutation: GuestSnapshotMutationRunner;
};

export function usePublicSeatingExportFlow(options: UsePublicSeatingExportFlowOptions) {
  return createClassroomPlannerPublicExportFlow<SeatingExportOption, "seating">({
    plannerState: options.plannerState,
    getSnapshot: options.getSnapshot,
    persistSnapshotMutation: options.persistSnapshotMutation,
    draftKind: "seating",
    defaultOption: "a3_landscape",
    exportSnapshot: exportPublicSeatingSnapshot,
    messages: {
      missingDraftMessage: "Öppna ett sittschema innan du exporterar.",
      initialStatusLabelForOption: (option) => {
        return option === "xlsx" ? "Förbereder Excel…" : "Förbereder affisch…";
      },
      successMessageForOption: (option) => {
        return option === "xlsx"
          ? "Excel-filen hämtades och exportcheckpointen sparades i den här webbläsaren."
          : "PDF-filen hämtades och exportcheckpointen sparades i den här webbläsaren.";
      },
      startErrorMessageForOption: (option) => {
        return option === "xlsx"
          ? "Det gick inte att exportera Excel-filen just nu."
          : "Det gick inte att exportera affischen just nu.";
      },
      fallbackDownloadName: (option) => {
        return option === "xlsx" ? "klassrumskarta.xlsx" : `klassrumskarta-${option}.pdf`;
      },
    },
  });
}
