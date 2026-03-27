/**
 * Shared classroom planner export-flow orchestration.
 *
 * This module owns the reusable export state machine shared by the seating and
 * grouping planner shells: flush pending draft work, create/poll export jobs,
 * restore recoverable jobs after reload, and trigger browser downloads.
 * Surface-specific wrappers inject draft-kind, API helpers, and teacher copy.
 */

import { computed, ref, watch } from "vue";

import { isApiError } from "../../api/client";
import { useToast } from "../../composables/useToast";
import type { PlanDraft, PlanDraftKind } from "./classroomPlannerTypes";
import type { PlannerTransitionResult } from "./plannerTransitionPolicies";

type ExportJobStatus = "submitted" | "processing" | "succeeded" | "failed";

type ExportArtifact = {
  name: string;
};

type ClassroomPlannerExportJobBase = {
  job_id: string;
  draft_id: string;
  export_kind: "pdf" | "xlsx";
  status: ExportJobStatus;
  vault_artifact: ExportArtifact | null;
  error: string | null;
};

type ClassroomPlannerExportPlannerState = {
  draft: PlanDraft | null;
  prepareForExport: (messages: {
    conflictMessage: string;
    fallbackMessage: string;
  }) => Promise<PlannerTransitionResult>;
};

type ClassroomPlannerExportFlowMessages<
  Job extends ClassroomPlannerExportJobBase,
  Option,
> = {
  missingDraftMessage: string;
  scopeChangedMessage: string;
  recoveryStatusMessage: string;
  genericExportErrorMessage: string;
  statusLabelForJob: (job: Job | null) => string | null;
  fallbackDownloadName: (job: Job) => string;
  initialStatusLabelForOption: (option: Option) => string;
  readyMessageForJob: (job: Job) => string;
  successMessageForJob: (job: Job) => string;
  autoDownloadFailureMessageForJob: (job: Job) => string;
  exportErrorMessageForJob: (job: Job) => string;
  restoreErrorMessageForJob: (job: Job) => string;
  startErrorMessageForOption: (option: Option) => string;
  downloadErrorMessageForJob: (job: Job) => string;
};

type CreateClassroomPlannerExportFlowOptions<
  Job extends ClassroomPlannerExportJobBase,
  Option,
  DraftKind extends PlanDraftKind,
> = {
  plannerState: ClassroomPlannerExportPlannerState;
  draftKind: DraftKind;
  defaultOption: Option;
  createJob: (draftId: string, option: Option) => Promise<Job>;
  getJob: (jobId: string) => Promise<Job>;
  getRecoverableJob: (draftId: string) => Promise<Job | null>;
  downloadJob: (jobId: string) => Promise<Blob>;
  messages: ClassroomPlannerExportFlowMessages<Job, Option>;
  pollDelayMs?: number;
  maxPollAttempts?: number;
};

type ExportScope = {
  draftId: string;
  token: number;
};

const DEFAULT_POLL_DELAY_MS = 1200;
const DEFAULT_MAX_POLL_ATTEMPTS = 75;

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

  constructor(jobId: string, message: string) {
    super(message);
    this.name = "ExportPollingTimeoutError";
    this.jobId = jobId;
  }
}

class ExportFlowScopeChangedError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ExportFlowScopeChangedError";
  }
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

export function createClassroomPlannerExportFlow<
  Job extends ClassroomPlannerExportJobBase,
  Option,
  DraftKind extends PlanDraftKind,
>(
  options: CreateClassroomPlannerExportFlowOptions<Job, Option, DraftKind>,
) {
  const toast = useToast();
  const pollDelayMs = options.pollDelayMs ?? DEFAULT_POLL_DELAY_MS;
  const maxPollAttempts = options.maxPollAttempts ?? DEFAULT_MAX_POLL_ATTEMPTS;
  const isStarting = ref(false);
  const activeJob = ref<Job | null>(null);
  const latestCompletedJob = ref<Job | null>(null);
  const statusLabel = ref<string | null>(null);
  const errorMessage = ref<string | null>(null);
  const backgroundPollJobId = ref<string | null>(null);
  const recoveryRestoreDraftId = ref<string | null>(null);
  const draftScopeToken = ref(0);

  const isBusy = computed(() => isStarting.value || activeJob.value !== null);
  const canDownloadLatest = computed(() => latestCompletedJob.value !== null && !isBusy.value);

  function getActiveDraftId(): string | null {
    const activeDraft = options.plannerState.draft;
    if (!activeDraft || activeDraft.draft_kind !== options.draftKind) {
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
    return draftScopeToken.value === scope.token && getActiveDraftId() === scope.draftId;
  }

  function ensureActiveScope(scope: ExportScope): void {
    if (!isActiveScope(scope)) {
      throw new ExportFlowScopeChangedError(options.messages.scopeChangedMessage);
    }
  }

  async function pollUntilComplete(
    jobId: string,
    maxAttempts: number,
    scope: ExportScope,
  ): Promise<Job> {
    let attemptsRemaining = maxAttempts;
    while (attemptsRemaining > 0) {
      const job = await options.getJob(jobId);
      ensureActiveScope(scope);
      activeJob.value = job;
      statusLabel.value = options.messages.statusLabelForJob(job);
      if (job.status === "succeeded") {
        return job;
      }
      if (job.status === "failed") {
        throw new Error(job.error ?? options.messages.exportErrorMessageForJob(job));
      }
      attemptsRemaining -= 1;
      if (attemptsRemaining <= 0) {
        throw new ExportPollingTimeoutError(jobId, options.messages.recoveryStatusMessage);
      }
      await wait(pollDelayMs);
    }
    throw new ExportPollingTimeoutError(jobId, options.messages.recoveryStatusMessage);
  }

  async function downloadCompletedJob(job: Job): Promise<void> {
    const blob = await options.downloadJob(job.job_id);
    triggerBrowserDownload(blob, job.vault_artifact?.name ?? options.messages.fallbackDownloadName(job));
  }

  async function finalizeCompletedJob(
    job: Job,
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
      statusLabel.value = finalizeOptions.readyMessage ?? options.messages.readyMessageForJob(job);
      return;
    }
    try {
      ensureActiveScope(scope);
      await downloadCompletedJob(job);
      ensureActiveScope(scope);
      const successMessage = finalizeOptions.successMessage ?? options.messages.successMessageForJob(job);
      statusLabel.value = successMessage;
      if (finalizeOptions.toastOnSuccess ?? true) {
        toast.success(successMessage);
      }
    } catch (error: unknown) {
      if (error instanceof ExportFlowScopeChangedError || !isActiveScope(scope)) {
        return;
      }
      statusLabel.value = finalizeOptions.readyMessage ?? options.messages.readyMessageForJob(job);
      errorMessage.value = normalizeExportError(
        error,
        options.messages.autoDownloadFailureMessageForJob(job),
      );
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
      if (error instanceof ExportFlowScopeChangedError || !isActiveScope(scope)) {
        return;
      }
      if (error instanceof ExportPollingTimeoutError) {
        statusLabel.value = options.messages.recoveryStatusMessage;
        return;
      }
      activeJob.value = null;
      backgroundPollJobId.value = null;
      statusLabel.value = null;
      errorMessage.value = normalizeExportError(
        error,
        activeJob.value
          ? options.messages.exportErrorMessageForJob(activeJob.value)
          : options.messages.genericExportErrorMessage,
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
      const recoveredJob = await options.getRecoverableJob(scope.draftId);
      ensureActiveScope(scope);
      if (!recoveredJob) {
        return;
      }
      if (recoveredJob.status === "succeeded") {
        await finalizeCompletedJob(recoveredJob, scope, {
          autoDownload: false,
          readyMessage: options.messages.readyMessageForJob(recoveredJob),
          toastOnSuccess: false,
        });
        return;
      }

      activeJob.value = recoveredJob;
      latestCompletedJob.value = null;
      statusLabel.value = options.messages.recoveryStatusMessage;
      void continuePollingInBackground(recoveredJob.job_id, scope, {
        autoDownload: false,
        readyMessage: options.messages.readyMessageForJob(recoveredJob),
      });
    } catch (error: unknown) {
      if (error instanceof ExportFlowScopeChangedError || !isActiveScope(scope)) {
        return;
      }
      activeJob.value = null;
      latestCompletedJob.value = null;
      backgroundPollJobId.value = null;
      statusLabel.value = null;
      errorMessage.value = normalizeExportError(
        error,
        activeJob.value
          ? options.messages.restoreErrorMessageForJob(activeJob.value)
          : "Kunde inte återställa exporten efter omladdning.",
      );
    }
  }

  async function startExport(option: Option): Promise<void> {
    if (isBusy.value) {
      return;
    }

    const initialDraftId = getActiveDraftId();
    if (!initialDraftId) {
      errorMessage.value = options.messages.missingDraftMessage;
      statusLabel.value = null;
      return;
    }

    const scope = {
      draftId: initialDraftId,
      token: draftScopeToken.value,
    } satisfies ExportScope;

    errorMessage.value = null;
    statusLabel.value = options.messages.initialStatusLabelForOption(option);
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
    if (!activeDraft || activeDraft.draft_kind !== options.draftKind) {
      throw new ExportFlowScopeChangedError(options.messages.scopeChangedMessage);
    }

    try {
      const createdJob = await options.createJob(activeDraft.id, option);
      ensureActiveScope(scope);
      isStarting.value = false;
      activeJob.value = createdJob;
      latestCompletedJob.value = null;
      statusLabel.value = options.messages.statusLabelForJob(createdJob);
      try {
        const completedJob = await pollUntilComplete(createdJob.job_id, maxPollAttempts, scope);
        await finalizeCompletedJob(completedJob, scope);
      } catch (error: unknown) {
        if (error instanceof ExportFlowScopeChangedError) {
          return;
        }
        if (error instanceof ExportPollingTimeoutError) {
          ensureActiveScope(scope);
          statusLabel.value = options.messages.recoveryStatusMessage;
          void continuePollingInBackground(error.jobId, scope);
          return;
        }
        throw error;
      }
    } catch (error: unknown) {
      if (error instanceof ExportFlowScopeChangedError || !isActiveScope(scope)) {
        return;
      }
      isStarting.value = false;
      activeJob.value = null;
      backgroundPollJobId.value = null;
      statusLabel.value = null;
      errorMessage.value = normalizeExportError(
        error,
        options.messages.startErrorMessageForOption(option),
      );
    }
  }

  async function downloadLatest(): Promise<void> {
    if (isBusy.value || !latestCompletedJob.value) {
      return;
    }
    errorMessage.value = null;
    try {
      await downloadCompletedJob(latestCompletedJob.value);
    } catch (error: unknown) {
      errorMessage.value = normalizeExportError(
        error,
        options.messages.downloadErrorMessageForJob(latestCompletedJob.value),
      );
    }
  }

  watch(
    () => options.plannerState.draft?.id ?? null,
    (draftId) => {
      draftScopeToken.value += 1;
      recoveryRestoreDraftId.value = null;
      if (!draftId || options.plannerState.draft?.draft_kind !== options.draftKind) {
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
    startDefaultExport: async () => await startExport(options.defaultOption),
    startExportOption: async (option: Option) => await startExport(option),
    downloadLatest,
  };
}
