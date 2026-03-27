/**
 * Grouping export orchestration for the planner route shell.
 *
 * This composable owns the explicit teacher-facing grouping export workflow:
 * flush pending autosave, create the export job, poll status, and restore
 * in-flight exports across reloads for both the local XLSX and local PDF
 * artifact lanes.
 */

import { computed, ref, watch } from "vue";

import { isApiError } from "../../api/client";
import { useToast } from "../../composables/useToast";
import {
  createGroupingExportJob,
  downloadGroupingExportJob,
  getGroupingExportJob,
  getRecoverableGroupingExportJob,
  type GroupingExportJob,
  type GroupingExportOption,
} from "./classroomPlannerExportApi";
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

type ExportScope = {
  draftId: string;
  token: number;
};

const DEFAULT_POLL_DELAY_MS = 1200;
const DEFAULT_MAX_POLL_ATTEMPTS = 75;
const RECOVERY_STATUS_MESSAGE = "Exporten tar längre tid än väntat. Vi fortsätter att kontrollera den.";

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
    super("Grouping export scope changed.");
    this.name = "ExportFlowScopeChangedError";
  }
}

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
    ? "Excel-filen hämtad och sparad i Mina filer."
    : "PDF hämtad och sparad i Mina filer.";
}

function autoDownloadFailureMessageForJob(job: GroupingExportJob): string {
  return job.export_kind === "xlsx"
    ? "Excel-filen skapades men kunde inte laddas ned automatiskt."
    : "PDF skapades men kunde inte laddas ned automatiskt.";
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

export function useGroupingExportFlow(options: UseGroupingExportFlowOptions) {
  const toast = useToast();
  const pollDelayMs = options.pollDelayMs ?? DEFAULT_POLL_DELAY_MS;
  const maxPollAttempts = options.maxPollAttempts ?? DEFAULT_MAX_POLL_ATTEMPTS;
  const isStarting = ref(false);
  const activeJob = ref<GroupingExportJob | null>(null);
  const latestCompletedJob = ref<GroupingExportJob | null>(null);
  const statusLabel = ref<string | null>(null);
  const errorMessage = ref<string | null>(null);
  const backgroundPollJobId = ref<string | null>(null);
  const recoveryRestoreDraftId = ref<string | null>(null);
  const draftScopeToken = ref(0);

  const isBusy = computed(() => isStarting.value || activeJob.value !== null);
  const canDownloadLatest = computed(() => latestCompletedJob.value !== null && !isBusy.value);

  function getActiveGroupingDraftId(): string | null {
    const activeDraft = options.plannerState.draft;
    if (!activeDraft || activeDraft.draft_kind !== "grouping") {
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
    return draftScopeToken.value === scope.token && getActiveGroupingDraftId() === scope.draftId;
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
  ): Promise<GroupingExportJob> {
    let attemptsRemaining = maxAttempts;
    while (attemptsRemaining > 0) {
      const job = await getGroupingExportJob(jobId);
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

  async function downloadJob(job: GroupingExportJob): Promise<void> {
    const blob = await downloadGroupingExportJob(job.job_id);
    triggerBrowserDownload(blob, job.vault_artifact?.name ?? fallbackDownloadName(job));
  }

  async function finalizeCompletedJob(
    job: GroupingExportJob,
    scope: ExportScope,
    finalizeOptions: {
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
    if (!finalizeOptions.autoDownload) {
      statusLabel.value = finalizeOptions.readyMessage ?? readyMessageForJob(job);
      return;
    }
    try {
      ensureActiveScope(scope);
      await downloadJob(job);
      ensureActiveScope(scope);
      const successMessage = finalizeOptions.successMessage ?? successMessageForJob(job);
      statusLabel.value = successMessage;
      if (finalizeOptions.toastOnSuccess ?? true) {
        toast.success(successMessage);
      }
    } catch (error: unknown) {
      if (error instanceof ExportFlowScopeChangedError) {
        return;
      }
      if (!isActiveScope(scope)) {
        return;
      }
      statusLabel.value = finalizeOptions.readyMessage ?? readyMessageForJob(job);
      errorMessage.value = normalizeExportError(error, autoDownloadFailureMessageForJob(job));
    }
  }

  async function continuePollingInBackground(
    jobId: string,
    scope: ExportScope,
    backgroundOptions: {
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
        autoDownload: backgroundOptions.autoDownload,
        readyMessage: backgroundOptions.readyMessage,
        toastOnSuccess: backgroundOptions.autoDownload,
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
      const recoveredJob = await getRecoverableGroupingExportJob(scope.draftId);
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

  async function startExport(option: GroupingExportOption): Promise<void> {
    if (isBusy.value) {
      return;
    }

    const initialDraftId = getActiveGroupingDraftId();
    if (!initialDraftId) {
      errorMessage.value = "Öppna en gruppindelning innan du exporterar.";
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

    const saveOutcome = await options.plannerState.prepareForExport({
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
    if (!activeDraft || activeDraft.draft_kind !== "grouping") {
      throw new ExportFlowScopeChangedError();
    }

    try {
      const createdJob = await createGroupingExportJob(activeDraft.id, option);
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
      errorMessage.value = normalizeExportError(error, startErrorMessageForOption(option));
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
      errorMessage.value = normalizeExportError(error, downloadErrorMessageForJob(latestCompletedJob.value));
    }
  }

  watch(
    () => options.plannerState.draft?.id ?? null,
    (draftId) => {
      draftScopeToken.value += 1;
      recoveryRestoreDraftId.value = null;
      if (!draftId || options.plannerState.draft?.draft_kind !== "grouping") {
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
    startDefaultExport: async () => await startExport("xlsx"),
    startExportOption: async (option: GroupingExportOption) => await startExport(option),
    downloadLatest,
  };
}
