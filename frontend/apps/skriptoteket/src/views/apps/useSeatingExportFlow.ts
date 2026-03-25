/**
 * Seating export orchestration for the planner route shell.
 *
 * This composable owns the explicit teacher-facing seating export workflow:
 * flush pending autosave, create the export job, poll status, and trigger
 * download on completion for both PDF posters and local XLSX workbooks.
 * Components stay presentational and only render the compact export affordance.
 */

import { computed, ref, watch } from "vue";

import { isApiError } from "../../api/client";
import { useToast } from "../../composables/useToast";
import {
  createSeatingExportJob,
  downloadSeatingExportJob,
  getRecoverableSeatingExportJob,
  getSeatingExportJob,
  type SeatingExportJob,
  type SeatingExportOption,
} from "./classroomPlannerExportApi";
import {
  flushPlannerRouteShellSave,
  type PlannerRouteShellSaveController,
} from "./classroomPlannerRouteShellSaveGuards";
import type { PlanDraft } from "./classroomPlannerTypes";

type SeatingExportPlannerState = PlannerRouteShellSaveController & {
  draft: PlanDraft | null;
};

type UseSeatingExportFlowOptions = {
  plannerState: SeatingExportPlannerState;
  pollDelayMs?: number;
  maxPollAttempts?: number;
};

const DEFAULT_POLL_DELAY_MS = 1200;
const DEFAULT_MAX_POLL_ATTEMPTS = 75;
const RECOVERY_STATUS_MESSAGE = "Exporten tar längre tid än väntat. Vi fortsätter att kontrollera den.";

type ExportScope = {
  draftId: string;
  token: number;
};

function wait(delayMs: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, delayMs));
}

function normalizeExportError(error: unknown, fallbackMessage: string): string {
  if (isApiError(error)) {
    return error.message || fallbackMessage;
  }
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return fallbackMessage;
}

class ExportPollingTimeoutError extends Error {
  jobId: string;

  constructor(jobId: string) {
    super(RECOVERY_STATUS_MESSAGE);
    this.name = "ExportPollingTimeoutError";
    this.jobId = jobId;
  }
}

class ExportFlowScopeChangedError extends Error {
  constructor() {
    super("Seating export scope changed.");
    this.name = "ExportFlowScopeChangedError";
  }
}

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

function readyMessageForJob(job: SeatingExportJob): string {
  return job.export_kind === "xlsx" ? "Excel klar för nedladdning." : "PDF klar för nedladdning.";
}

function successMessageForJob(job: SeatingExportJob): string {
  return job.export_kind === "xlsx"
    ? "Excel-filen hämtad och sparad i Mina filer."
    : "PDF hämtad och sparad i Mina filer.";
}

function autoDownloadFailureMessageForJob(job: SeatingExportJob): string {
  return job.export_kind === "xlsx"
    ? "Excel-filen skapades men kunde inte laddas ned automatiskt."
    : "PDF skapades men kunde inte laddas ned automatiskt.";
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

function downloadErrorMessageForJob(job: SeatingExportJob): string {
  return job.export_kind === "xlsx"
    ? "Det gick inte att ladda ned Excel-filen."
    : "Det gick inte att ladda ned PDF-filen.";
}

function triggerBrowserDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.style.display = "none";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.setTimeout(() => URL.revokeObjectURL(url), 0);
}

export function useSeatingExportFlow(options: UseSeatingExportFlowOptions) {
  const toast = useToast();
  const pollDelayMs = options.pollDelayMs ?? DEFAULT_POLL_DELAY_MS;
  const maxPollAttempts = options.maxPollAttempts ?? DEFAULT_MAX_POLL_ATTEMPTS;
  const isStarting = ref(false);
  const activeJob = ref<SeatingExportJob | null>(null);
  const latestCompletedJob = ref<SeatingExportJob | null>(null);
  const statusLabel = ref<string | null>(null);
  const errorMessage = ref<string | null>(null);
  const backgroundPollJobId = ref<string | null>(null);
  const recoveryRestoreDraftId = ref<string | null>(null);
  const draftScopeToken = ref(0);

  const isBusy = computed(() => isStarting.value || activeJob.value !== null);
  const canDownloadLatest = computed(() => latestCompletedJob.value !== null && !isBusy.value);

  function getActiveSeatingDraftId(): string | null {
    const activeDraft = options.plannerState.draft;
    if (!activeDraft || activeDraft.draft_kind !== "seating") {
      return null;
    }
    return activeDraft.id;
  }

  function resetExportState(): void {
    isStarting.value = false;
    activeJob.value = null;
    latestCompletedJob.value = null;
    backgroundPollJobId.value = null;
    statusLabel.value = null;
    errorMessage.value = null;
  }

  function isActiveScope(scope: ExportScope): boolean {
    return (
      draftScopeToken.value === scope.token
      && getActiveSeatingDraftId() === scope.draftId
    );
  }

  function ensureActiveScope(scope: ExportScope): void {
    if (!isActiveScope(scope)) {
      throw new ExportFlowScopeChangedError();
    }
  }

  async function pollUntilComplete(
    jobId: string,
    maxAttempts: number,
    scope: ExportScope,
  ): Promise<SeatingExportJob> {
    let attemptsRemaining = maxAttempts;
    while (attemptsRemaining > 0) {
      const job = await getSeatingExportJob(jobId);
      ensureActiveScope(scope);
      activeJob.value = job;
      statusLabel.value = statusLabelForJob(job);
      if (job.status === "succeeded") {
        return job;
      }
      if (job.status === "failed") {
        throw new Error(job.error ?? exportErrorMessageForJob(job));
      }
      attemptsRemaining -= 1;
      if (attemptsRemaining <= 0) {
        throw new ExportPollingTimeoutError(jobId);
      }
      await wait(pollDelayMs);
    }
    throw new ExportPollingTimeoutError(jobId);
  }

  async function downloadJob(job: SeatingExportJob): Promise<void> {
    const blob = await downloadSeatingExportJob(job.job_id);
    triggerBrowserDownload(blob, job.vault_artifact?.name ?? fallbackDownloadName(job));
  }

  async function finalizeCompletedJob(
    job: SeatingExportJob,
    scope: ExportScope,
    options: {
      autoDownload: boolean;
      successMessage?: string;
      readyMessage?: string;
      toastOnSuccess?: boolean;
    } = {
      autoDownload: true,
      toastOnSuccess: true,
    },
  ): Promise<void> {
    ensureActiveScope(scope);
    latestCompletedJob.value = job;
    activeJob.value = null;
    backgroundPollJobId.value = null;
    if (!options.autoDownload) {
      statusLabel.value = options.readyMessage ?? readyMessageForJob(job);
      return;
    }
    try {
      ensureActiveScope(scope);
      await downloadJob(job);
      ensureActiveScope(scope);
      const successMessage = options.successMessage ?? successMessageForJob(job);
      statusLabel.value = successMessage;
      if (options.toastOnSuccess ?? true) {
        toast.success(successMessage);
      }
    } catch (error: unknown) {
      if (error instanceof ExportFlowScopeChangedError) {
        return;
      }
      if (!isActiveScope(scope)) {
        return;
      }
      statusLabel.value = options.readyMessage ?? readyMessageForJob(job);
      errorMessage.value = normalizeExportError(
        error,
        autoDownloadFailureMessageForJob(job),
      );
    }
  }

  async function continuePollingInBackground(
    jobId: string,
    scope: ExportScope,
    options: {
      autoDownload: boolean;
      readyMessage?: string;
    } = {
      autoDownload: true,
    },
  ): Promise<void> {
    const backgroundPollKey = `${scope.draftId}:${jobId}`;
    if (backgroundPollJobId.value === backgroundPollKey) {
      return;
    }
    backgroundPollJobId.value = backgroundPollKey;
    try {
      const completedJob = await pollUntilComplete(jobId, Number.MAX_SAFE_INTEGER, scope);
      await finalizeCompletedJob(completedJob, scope, {
        autoDownload: options.autoDownload,
        readyMessage: options.readyMessage,
        toastOnSuccess: options.autoDownload,
      });
    } catch (error: unknown) {
      if (error instanceof ExportFlowScopeChangedError) {
        return;
      }
      if (!isActiveScope(scope)) {
        return;
      }
      if (error instanceof ExportPollingTimeoutError) {
        statusLabel.value = RECOVERY_STATUS_MESSAGE;
        return;
      }
      activeJob.value = null;
      backgroundPollJobId.value = null;
      statusLabel.value = null;
      errorMessage.value = normalizeExportError(
        error,
        activeJob.value ? exportErrorMessageForJob(activeJob.value) : "Det gick inte att exportera filen just nu.",
      );
    }
  }

  async function restoreRecoverableExportForActiveDraft(scope: ExportScope): Promise<void> {
    ensureActiveScope(scope);
    if (recoveryRestoreDraftId.value === scope.draftId) {
      return;
    }
    recoveryRestoreDraftId.value = scope.draftId;
    if (isStarting.value || activeJob.value !== null) {
      return;
    }

    try {
      const recoveredJob = await getRecoverableSeatingExportJob(scope.draftId);
      ensureActiveScope(scope);
      if (!recoveredJob) {
        return;
      }
      if (recoveredJob.status === "succeeded") {
        await finalizeCompletedJob(recoveredJob, scope, {
          autoDownload: false,
          readyMessage: readyMessageForJob(recoveredJob),
          toastOnSuccess: false,
        });
        return;
      }

      activeJob.value = recoveredJob;
      latestCompletedJob.value = null;
      statusLabel.value = RECOVERY_STATUS_MESSAGE;
      void continuePollingInBackground(recoveredJob.job_id, scope, {
        autoDownload: false,
        readyMessage: readyMessageForJob(recoveredJob),
      });
    } catch (error: unknown) {
      if (error instanceof ExportFlowScopeChangedError) {
        return;
      }
      if (!isActiveScope(scope)) {
        return;
      }
      activeJob.value = null;
      latestCompletedJob.value = null;
      backgroundPollJobId.value = null;
      statusLabel.value = null;
      errorMessage.value = normalizeExportError(
        error,
        activeJob.value ? restoreErrorMessageForJob(activeJob.value) : "Kunde inte återställa exporten efter omladdning.",
      );
    }
  }

  async function startExport(option: SeatingExportOption): Promise<void> {
    if (isBusy.value) {
      return;
    }

    const initialDraftId = getActiveSeatingDraftId();
    if (!initialDraftId) {
      errorMessage.value = "Öppna ett sittschema innan du exporterar.";
      statusLabel.value = null;
      return;
    }

    const scope = {
      draftId: initialDraftId,
      token: draftScopeToken.value,
    } satisfies ExportScope;

    errorMessage.value = null;
    statusLabel.value = initialStatusLabelForOption(option);
    isStarting.value = true;

    const saveOutcome = await flushPlannerRouteShellSave(options.plannerState, {
      conflictMessage: "Lös sparkonflikten innan du exporterar.",
      fallbackMessage: "Kunde inte spara ändringarna innan export.",
    });
    if (saveOutcome.status === "blocked") {
      if (!isActiveScope(scope)) {
        return;
      }
      isStarting.value = false;
      errorMessage.value = saveOutcome.message;
      statusLabel.value = null;
      return;
    }

    if (!isActiveScope(scope)) {
      return;
    }
    const activeDraft = options.plannerState.draft;
    if (!activeDraft || activeDraft.draft_kind !== "seating") {
      throw new ExportFlowScopeChangedError();
    }

    try {
      const createdJob = await createSeatingExportJob(activeDraft.id, option);
      ensureActiveScope(scope);
      isStarting.value = false;
      activeJob.value = createdJob;
      latestCompletedJob.value = null;
      statusLabel.value = statusLabelForJob(createdJob);
      try {
        const completedJob = await pollUntilComplete(createdJob.job_id, maxPollAttempts, scope);
        await finalizeCompletedJob(completedJob, scope);
      } catch (error: unknown) {
        if (error instanceof ExportFlowScopeChangedError) {
          return;
        }
        if (error instanceof ExportPollingTimeoutError) {
          ensureActiveScope(scope);
          statusLabel.value = RECOVERY_STATUS_MESSAGE;
          void continuePollingInBackground(error.jobId, scope);
          return;
        }
        throw error;
      }
    } catch (error: unknown) {
      if (error instanceof ExportFlowScopeChangedError) {
        return;
      }
      if (!isActiveScope(scope)) {
        return;
      }
      isStarting.value = false;
      activeJob.value = null;
      backgroundPollJobId.value = null;
      statusLabel.value = null;
      errorMessage.value = normalizeExportError(
        error,
        startErrorMessageForOption(option),
      );
    }
  }

  async function downloadLatest(): Promise<void> {
    if (isBusy.value || !latestCompletedJob.value) {
      return;
    }
    errorMessage.value = null;
    try {
      await downloadJob(latestCompletedJob.value);
    } catch (error: unknown) {
      errorMessage.value = normalizeExportError(
        error,
        downloadErrorMessageForJob(latestCompletedJob.value),
      );
    }
  }

  watch(
    () => options.plannerState.draft?.id ?? null,
    (draftId) => {
      draftScopeToken.value += 1;
      recoveryRestoreDraftId.value = null;
      if (!draftId || options.plannerState.draft?.draft_kind !== "seating") {
        resetExportState();
        return;
      }
      resetExportState();
      const scope = {
        draftId,
        token: draftScopeToken.value,
      } satisfies ExportScope;
      void restoreRecoverableExportForActiveDraft(scope);
    },
    { immediate: true },
  );

  return {
    isBusy,
    statusLabel,
    errorMessage,
    canDownloadLatest,
    startDefaultExport: async () => await startExport("a3_landscape"),
    startExportOption: async (option: SeatingExportOption) => await startExport(option),
    downloadLatest,
  };
}
