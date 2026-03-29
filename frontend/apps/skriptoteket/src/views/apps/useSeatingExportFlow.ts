/**
 * Seating export orchestration for the planner route shell.
 *
 * This composable injects seating-specific API helpers and teacher copy into
 * the shared planner export state machine so the route shell keeps a dedicated
 * seating export surface without duplicating the generic polling/recovery flow.
 */

import {
  createSeatingExportJob,
  downloadSeatingExportJob,
  getRecoverableSeatingExportJob,
  getSeatingExportJob,
  type SeatingExportJob,
  type SeatingExportOption,
} from "./classroomPlannerExportApi";
import { createClassroomPlannerExportFlow } from "./classroomPlannerExportFlow";
import type { PlanDraft } from "./classroomPlannerTypes";
import type { PlannerTransitionResult } from "./plannerTransitionPolicies";

type SeatingExportPlannerState = {
  draft: PlanDraft | null;
  prepareForExport: (messages: {
    conflictMessage: string;
    fallbackMessage: string;
  }) => Promise<PlannerTransitionResult>;
};

type UseSeatingExportFlowOptions = {
  plannerState: SeatingExportPlannerState;
  pollDelayMs?: number;
  maxPollAttempts?: number;
};

const RECOVERY_STATUS_MESSAGE = "Exporten tar längre tid än väntat. Vi fortsätter att kontrollera den.";

function statusLabelForJob(job: SeatingExportJob | null): string | null {
  if (!job) {
    return null;
  }
  if (job.export_kind === "xlsx") {
    return job.status === "processing" ? "Skapar Excel…" : "Förbereder Excel…";
  }
  return job.status === "processing" ? "Skapar PDF…" : "Förbereder affisch…";
}

function fallbackDownloadName(job: SeatingExportJob): string {
  if (job.export_kind === "xlsx") {
    return "klassrumskarta.xlsx";
  }
  return `klassrumskarta-${job.paper_size ?? "export"}.pdf`;
}

function initialStatusLabelForOption(option: SeatingExportOption): string {
  return option === "xlsx" ? "Förbereder Excel…" : "Förbereder affisch…";
}

function successMessageForJob(job: SeatingExportJob): string {
  return job.export_kind === "xlsx"
    ? "Excel-filen hämtad och sparad i Mina filer. Hämta den där igen vid behov."
    : "PDF hämtad och sparad i Mina filer. Hämta den där igen vid behov.";
}

function recoveredSuccessMessageForJob(job: SeatingExportJob): string {
  return job.export_kind === "xlsx"
    ? "Excel klar och sparad i Mina filer. Hämta den där igen vid behov."
    : "PDF klar och sparad i Mina filer. Hämta den där igen vid behov.";
}

function autoDownloadFailureMessageForJob(job: SeatingExportJob): string {
  return job.export_kind === "xlsx"
    ? "Excel-filen skapades men kunde inte laddas ned automatiskt. Hämta den i Mina filer."
    : "PDF skapades men kunde inte laddas ned automatiskt. Hämta den i Mina filer.";
}

function exportErrorMessageForJob(job: SeatingExportJob): string {
  return job.export_kind === "xlsx"
    ? "Det gick inte att exportera Excel-filen just nu."
    : "Det gick inte att exportera affischen just nu.";
}

function restoreErrorMessageForJob(job: SeatingExportJob): string {
  return job.export_kind === "xlsx"
    ? "Kunde inte återställa Excel-exporten efter omladdning."
    : "Kunde inte återställa PDF-exporten efter omladdning.";
}

function startErrorMessageForOption(option: SeatingExportOption): string {
  return option === "xlsx"
    ? "Det gick inte att exportera Excel-filen just nu."
    : "Det gick inte att exportera affischen just nu.";
}

export function useSeatingExportFlow(options: UseSeatingExportFlowOptions) {
  return createClassroomPlannerExportFlow<SeatingExportJob, SeatingExportOption, "seating">({
    plannerState: options.plannerState,
    draftKind: "seating",
    defaultOption: "a3_landscape",
    createJob: createSeatingExportJob,
    getJob: getSeatingExportJob,
    getRecoverableJob: getRecoverableSeatingExportJob,
    downloadJob: downloadSeatingExportJob,
    messages: {
      missingDraftMessage: "Öppna ett sittschema innan du exporterar.",
      scopeChangedMessage: "Seating export scope changed.",
      recoveryStatusMessage: RECOVERY_STATUS_MESSAGE,
      genericExportErrorMessage: "Det gick inte att exportera filen just nu.",
      statusLabelForJob,
      fallbackDownloadName,
      initialStatusLabelForOption,
      successMessageForJob,
      recoveredSuccessMessageForJob,
      autoDownloadFailureMessageForJob,
      exportErrorMessageForJob,
      restoreErrorMessageForJob,
      startErrorMessageForOption,
    },
    pollDelayMs: options.pollDelayMs,
    maxPollAttempts: options.maxPollAttempts,
  });
}
