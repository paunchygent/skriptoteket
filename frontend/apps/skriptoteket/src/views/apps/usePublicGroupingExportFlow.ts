/**
 * Grouping public export orchestration for the guest planner shell.
 *
 * This composable injects grouping-specific copy and API helpers into the
 * guest direct-download export flow so the public lane can reuse the shared
 * toolbar without inheriting authenticated export-job semantics.
 */

import type { Ref } from "vue";

import { createClassroomPlannerPublicExportFlow } from "./classroomPlannerPublicExportFlow";
import { exportPublicGroupingSnapshot } from "./classroomPlannerPublicExportApi";
import type { GuestSnapshotMutationRunner } from "./classroomPlannerGuestDraftPersistence";
import type { ClassroomPlannerGuestSnapshot } from "./classroomPlannerGuestSnapshot";
import type { GroupingExportOption } from "./classroomPlannerExportApi";
import type { PlanDraft } from "./classroomPlannerTypes";
import type { PlannerTransitionResult } from "./plannerTransitionPolicies";

type GroupingExportPlannerState = {
  draft: PlanDraft | null | Ref<PlanDraft | null>;
  prepareForExport: (messages: {
    conflictMessage: string;
    fallbackMessage: string;
  }) => Promise<PlannerTransitionResult>;
};

type UsePublicGroupingExportFlowOptions = {
  plannerState: GroupingExportPlannerState;
  getSnapshot: () => Promise<ClassroomPlannerGuestSnapshot>;
  persistSnapshotMutation: GuestSnapshotMutationRunner;
};

export function usePublicGroupingExportFlow(options: UsePublicGroupingExportFlowOptions) {
  return createClassroomPlannerPublicExportFlow<GroupingExportOption, "grouping">({
    plannerState: options.plannerState,
    getSnapshot: options.getSnapshot,
    persistSnapshotMutation: options.persistSnapshotMutation,
    draftKind: "grouping",
    defaultOption: "xlsx",
    exportSnapshot: exportPublicGroupingSnapshot,
    messages: {
      missingDraftMessage: "Öppna en gruppindelning innan du exporterar.",
      initialStatusLabelForOption: (option) => {
        return option === "xlsx" ? "Förbereder Excel…" : "Förbereder PDF…";
      },
      successMessageForOption: (option) => {
        return option === "xlsx"
          ? "Excel-filen hämtades och exportcheckpointen sparades i den här webbläsaren."
          : "PDF-filen hämtades och exportcheckpointen sparades i den här webbläsaren.";
      },
      startErrorMessageForOption: (option) => {
        return option === "xlsx"
          ? "Det gick inte att exportera Excel-filen just nu."
          : "Det gick inte att exportera PDF-filen just nu.";
      },
      fallbackDownloadName: (option) => {
        return option === "xlsx" ? "gruppindelning.xlsx" : "gruppindelning-a4.pdf";
      },
    },
  });
}
