/**
 * Grouping export orchestration for the planner route shell.
 *
 * This composable injects grouping-specific API helpers and teacher copy into
 * the shared planner export state machine so grouping export keeps its own
 * surface without duplicating the generic create/poll/recovery orchestration.
 */

import {
  createGroupingExportJob,
  downloadGroupingExportJob,
  getGroupingExportJob,
  getRecoverableGroupingExportJob,
  type GroupingExportJob,
  type GroupingExportOption,
} from "./classroomPlannerExportApi";
import { createClassroomPlannerExportFlow } from "./classroomPlannerExportFlow";
import type { PlanDraft } from "./classroomPlannerTypes";
import type { PlannerTransitionResult } from "./plannerTransitionPolicies";

type GroupingExportPlannerState = {
  draft: PlanDraft | null;
  prepareForExport: (messages: {
    conflictMessage: string;
    fallbackMessage: string;
  }) => Promise<PlannerTransitionResult>;
};

type UseGroupingExportFlowOptions = {
  plannerState: GroupingExportPlannerState;
  pollDelayMs?: number;
  maxPollAttempts?: number;
};

const RECOVERY_STATUS_MESSAGE = "Exporten tar längre tid än väntat. Vi fortsätter att kontrollera den.";

function statusLabelForJob(job: GroupingExportJob | null): string | null {
  if (!job) {
    return null;
  }
  if (job.export_kind === "xlsx") {
    return job.status === "processing" ? "Skapar Excel…" : "Förbereder Excel…";
  }
  return job.status === "processing" ? "Skapar PDF…" : "Förbereder PDF…";
}

function fallbackDownloadName(job: GroupingExportJob): string {
  if (job.export_kind === "xlsx") {
    return "gruppindelning.xlsx";
  }
  return "gruppindelning-a4.pdf";
}

function initialStatusLabelForOption(option: GroupingExportOption): string {
  return option === "xlsx" ? "Förbereder Excel…" : "Förbereder PDF…";
}

function readyMessageForJob(job: GroupingExportJob): string {
  return job.export_kind === "xlsx" ? "Excel klar för nedladdning." : "PDF klar för nedladdning.";
}

function successMessageForJob(job: GroupingExportJob): string {
  return job.export_kind === "xlsx"
    ? "Excel-filen hämtad och sparad i Mina filer. Hämta den där igen vid behov."
    : "PDF hämtad och sparad i Mina filer. Hämta den där igen vid behov.";
}

function autoDownloadFailureMessageForJob(job: GroupingExportJob): string {
  return job.export_kind === "xlsx"
    ? "Excel-filen skapades men kunde inte laddas ned automatiskt. Hämta den i Mina filer."
    : "PDF skapades men kunde inte laddas ned automatiskt. Hämta den i Mina filer.";
}

function exportErrorMessageForJob(job: GroupingExportJob): string {
  return job.export_kind === "xlsx"
    ? "Det gick inte att exportera Excel-filen just nu."
    : "Det gick inte att exportera PDF-filen just nu.";
}

function restoreErrorMessageForJob(job: GroupingExportJob): string {
  return job.export_kind === "xlsx"
    ? "Kunde inte återställa Excel-exporten efter omladdning."
    : "Kunde inte återställa PDF-exporten efter omladdning.";
}

function startErrorMessageForOption(option: GroupingExportOption): string {
  return option === "xlsx"
    ? "Det gick inte att exportera Excel-filen just nu."
    : "Det gick inte att exportera PDF-filen just nu.";
}

function downloadErrorMessageForJob(job: GroupingExportJob): string {
  return job.export_kind === "xlsx"
    ? "Det gick inte att ladda ned Excel-filen."
    : "Det gick inte att ladda ned PDF-filen.";
}

export function useGroupingExportFlow(options: UseGroupingExportFlowOptions) {
  return createClassroomPlannerExportFlow<GroupingExportJob, GroupingExportOption, "grouping">({
    plannerState: options.plannerState,
    draftKind: "grouping",
    defaultOption: "xlsx",
    createJob: createGroupingExportJob,
    getJob: getGroupingExportJob,
    getRecoverableJob: getRecoverableGroupingExportJob,
    downloadJob: downloadGroupingExportJob,
    messages: {
      missingDraftMessage: "Öppna en gruppindelning innan du exporterar.",
      scopeChangedMessage: "Grouping export scope changed.",
      recoveryStatusMessage: RECOVERY_STATUS_MESSAGE,
      genericExportErrorMessage: "Det gick inte att exportera filen just nu.",
      statusLabelForJob,
      fallbackDownloadName,
      initialStatusLabelForOption,
      readyMessageForJob,
      successMessageForJob,
      autoDownloadFailureMessageForJob,
      exportErrorMessageForJob,
      restoreErrorMessageForJob,
      startErrorMessageForOption,
      downloadErrorMessageForJob,
    },
    pollDelayMs: options.pollDelayMs,
    maxPollAttempts: options.maxPollAttempts,
  });
}
