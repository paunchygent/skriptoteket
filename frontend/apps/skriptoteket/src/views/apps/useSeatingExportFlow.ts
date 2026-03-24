/**
 * Seating export orchestration for the planner route shell.
 *
 * This composable owns the explicit teacher-facing export workflow for seating
 * posters: flush pending autosave, create the async export job, poll status,
 * and trigger download on completion. Components stay presentational and only
 * render the compact export affordance.
 */

import { computed, ref, watch } from "vue";

import { isApiError } from "../../api/client";
import { useToast } from "../../composables/useToast";
import {
  createSeatingExportJob,
  downloadSeatingExportJob,
  getSeatingExportJob,
  type SeatingExportJob,
  type SeatingExportPaperSize,
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
const RECOVERY_STATUS_MESSAGE = "PDF-exporten tar längre tid än väntat. Vi fortsätter att kontrollera den.";
const RECOVERY_READY_MESSAGE = "PDF klar för nedladdning.";
const EXPORT_RECOVERY_STORAGE_KEY = "skriptoteket:classroom-planner:seating-export-recovery";

type PersistedExportRecoveryState = {
  draftId: string;
  activeJobId: string | null;
  latestCompletedJobId: string | null;
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

function getSessionStorage(): Storage | null {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    return window.sessionStorage;
  } catch {
    return null;
  }
}

function readPersistedExportRecoveryState(): PersistedExportRecoveryState | null {
  const storage = getSessionStorage();
  const rawValue = storage?.getItem(EXPORT_RECOVERY_STORAGE_KEY);
  if (!rawValue) {
    return null;
  }
  try {
    const parsed = JSON.parse(rawValue) as Record<string, unknown>;
    if (
      typeof parsed.draftId !== "string"
      || (parsed.activeJobId !== null && typeof parsed.activeJobId !== "string")
      || (parsed.latestCompletedJobId !== null
        && typeof parsed.latestCompletedJobId !== "string")
    ) {
      return null;
    }
    return {
      draftId: parsed.draftId,
      activeJobId: parsed.activeJobId,
      latestCompletedJobId: parsed.latestCompletedJobId,
    };
  } catch {
    return null;
  }
}

function writePersistedExportRecoveryState(state: PersistedExportRecoveryState | null): void {
  const storage = getSessionStorage();
  if (!storage) {
    return;
  }
  if (
    !state
    || (state.activeJobId === null && state.latestCompletedJobId === null)
    || state.draftId.trim() === ""
  ) {
    storage.removeItem(EXPORT_RECOVERY_STORAGE_KEY);
    return;
  }
  storage.setItem(EXPORT_RECOVERY_STORAGE_KEY, JSON.stringify(state));
}

class ExportPollingTimeoutError extends Error {
  jobId: string;

  constructor(jobId: string) {
    super(RECOVERY_STATUS_MESSAGE);
    this.name = "ExportPollingTimeoutError";
    this.jobId = jobId;
  }
}

function statusLabelForJob(job: SeatingExportJob | null): string | null {
  if (!job) {
    return null;
  }
  return job.status === "processing" ? "Skapar PDF…" : "Förbereder affisch…";
}

function fallbackDownloadName(job: SeatingExportJob): string {
  return `klassrumskarta-${job.paper_size}.pdf`;
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

  const isBusy = computed(() => isStarting.value || activeJob.value !== null);
  const canDownloadLatest = computed(() => latestCompletedJob.value !== null && !isBusy.value);

  function persistRecoveryState(): void {
    const draftId =
      activeJob.value?.draft_id
      ?? latestCompletedJob.value?.draft_id
      ?? (options.plannerState.draft?.draft_kind === "seating" ? options.plannerState.draft.id : null);
    writePersistedExportRecoveryState(
      draftId
        ? {
            draftId,
            activeJobId: activeJob.value?.job_id ?? null,
            latestCompletedJobId: latestCompletedJob.value?.job_id ?? null,
          }
        : null,
    );
  }

  async function pollUntilComplete(jobId: string, maxAttempts: number): Promise<SeatingExportJob> {
    let attemptsRemaining = maxAttempts;
    while (attemptsRemaining > 0) {
      const job = await getSeatingExportJob(jobId);
      activeJob.value = job;
      statusLabel.value = statusLabelForJob(job);
      if (job.status === "succeeded") {
        return job;
      }
      if (job.status === "failed") {
        throw new Error(job.error ?? "Det gick inte att exportera affischen just nu.");
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
    options: {
      autoDownload: boolean;
      successMessage?: string;
      readyMessage?: string;
      toastOnSuccess?: boolean;
    } = {
      autoDownload: true,
      successMessage: "PDF hämtad och sparad i Mina filer.",
      readyMessage: RECOVERY_READY_MESSAGE,
      toastOnSuccess: true,
    },
  ): Promise<void> {
    latestCompletedJob.value = job;
    activeJob.value = null;
    backgroundPollJobId.value = null;
    persistRecoveryState();
    if (!options.autoDownload) {
      statusLabel.value = options.readyMessage ?? RECOVERY_READY_MESSAGE;
      return;
    }
    try {
      await downloadJob(job);
      statusLabel.value = options.successMessage ?? "PDF hämtad och sparad i Mina filer.";
      if (options.toastOnSuccess ?? true) {
        toast.success(options.successMessage ?? "PDF hämtad och sparad i Mina filer.");
      }
    } catch (error: unknown) {
      statusLabel.value = options.readyMessage ?? RECOVERY_READY_MESSAGE;
      errorMessage.value = normalizeExportError(
        error,
        "PDF skapades men kunde inte laddas ned automatiskt.",
      );
    }
  }

  async function continuePollingInBackground(
    jobId: string,
    options: {
      autoDownload: boolean;
      readyMessage?: string;
    } = {
      autoDownload: true,
      readyMessage: RECOVERY_READY_MESSAGE,
    },
  ): Promise<void> {
    if (backgroundPollJobId.value === jobId) {
      return;
    }
    backgroundPollJobId.value = jobId;
    try {
      const completedJob = await pollUntilComplete(jobId, Number.MAX_SAFE_INTEGER);
      await finalizeCompletedJob(completedJob, {
        autoDownload: options.autoDownload,
        readyMessage: options.readyMessage,
        successMessage: "PDF hämtad och sparad i Mina filer.",
        toastOnSuccess: options.autoDownload,
      });
    } catch (error: unknown) {
      if (error instanceof ExportPollingTimeoutError) {
        statusLabel.value = RECOVERY_STATUS_MESSAGE;
        return;
      }
      activeJob.value = null;
      backgroundPollJobId.value = null;
      statusLabel.value = null;
      persistRecoveryState();
      errorMessage.value = normalizeExportError(
        error,
        "Det gick inte att exportera affischen just nu.",
      );
    }
  }

  async function restorePersistedExportRecovery(): Promise<void> {
    const activeDraft = options.plannerState.draft;
    if (!activeDraft || activeDraft.draft_kind !== "seating") {
      return;
    }
    if (recoveryRestoreDraftId.value === activeDraft.id) {
      return;
    }
    recoveryRestoreDraftId.value = activeDraft.id;
    if (isStarting.value || activeJob.value !== null) {
      persistRecoveryState();
      return;
    }

    const persisted = readPersistedExportRecoveryState();
    if (!persisted || persisted.draftId !== activeDraft.id) {
      return;
    }

    errorMessage.value = null;

    if (persisted.latestCompletedJobId) {
      try {
        const latestJob = await getSeatingExportJob(persisted.latestCompletedJobId);
        if (latestJob.status === "succeeded") {
          latestCompletedJob.value = latestJob;
          statusLabel.value = RECOVERY_READY_MESSAGE;
          persistRecoveryState();
        }
      } catch {
        latestCompletedJob.value = null;
        persistRecoveryState();
      }
    }

    if (!persisted.activeJobId) {
      return;
    }

    try {
      const recoveredJob = await getSeatingExportJob(persisted.activeJobId);
      if (recoveredJob.status === "succeeded") {
        await finalizeCompletedJob(recoveredJob, {
          autoDownload: false,
          readyMessage: RECOVERY_READY_MESSAGE,
          toastOnSuccess: false,
        });
        return;
      }
      if (recoveredJob.status === "failed") {
        activeJob.value = null;
        statusLabel.value = null;
        persistRecoveryState();
        errorMessage.value = recoveredJob.error ?? "Det gick inte att exportera affischen just nu.";
        return;
      }

      activeJob.value = recoveredJob;
      statusLabel.value = RECOVERY_STATUS_MESSAGE;
      persistRecoveryState();
      void continuePollingInBackground(recoveredJob.job_id, {
        autoDownload: false,
        readyMessage: RECOVERY_READY_MESSAGE,
      });
    } catch (error: unknown) {
      activeJob.value = null;
      backgroundPollJobId.value = null;
      statusLabel.value = latestCompletedJob.value ? RECOVERY_READY_MESSAGE : null;
      persistRecoveryState();
      errorMessage.value = normalizeExportError(
        error,
        "Kunde inte återställa PDF-exporten efter omladdning.",
      );
    }
  }

  async function startExport(paperSize: SeatingExportPaperSize): Promise<void> {
    if (isBusy.value) {
      return;
    }

    if (!options.plannerState.draft || options.plannerState.draft.draft_kind !== "seating") {
      errorMessage.value = "Öppna ett sittschema innan du exporterar.";
      statusLabel.value = null;
      return;
    }

    errorMessage.value = null;
    statusLabel.value = "Förbereder affisch…";
    isStarting.value = true;

    const saveOutcome = await flushPlannerRouteShellSave(options.plannerState, {
      conflictMessage: "Lös sparkonflikten innan du exporterar.",
      fallbackMessage: "Kunde inte spara ändringarna innan export.",
    });
    if (saveOutcome.status === "blocked") {
      isStarting.value = false;
      errorMessage.value = saveOutcome.message;
      statusLabel.value = null;
      return;
    }

    const activeDraft = options.plannerState.draft;
    if (!activeDraft || activeDraft.draft_kind !== "seating") {
      isStarting.value = false;
      errorMessage.value = "Öppna ett sittschema innan du exporterar.";
      statusLabel.value = null;
      return;
    }

    try {
      const createdJob = await createSeatingExportJob(activeDraft.id, paperSize);
      isStarting.value = false;
      activeJob.value = createdJob;
      persistRecoveryState();
      statusLabel.value = statusLabelForJob(createdJob);
      try {
        const completedJob = await pollUntilComplete(createdJob.job_id, maxPollAttempts);
        await finalizeCompletedJob(completedJob);
      } catch (error: unknown) {
        if (error instanceof ExportPollingTimeoutError) {
          statusLabel.value = RECOVERY_STATUS_MESSAGE;
          void continuePollingInBackground(error.jobId);
          return;
        }
        throw error;
      }
    } catch (error: unknown) {
      isStarting.value = false;
      activeJob.value = null;
      backgroundPollJobId.value = null;
      statusLabel.value = null;
      persistRecoveryState();
      errorMessage.value = normalizeExportError(
        error,
        "Det gick inte att exportera affischen just nu.",
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
      errorMessage.value = normalizeExportError(error, "Det gick inte att ladda ned PDF-filen.");
    }
  }

  watch(
    () => options.plannerState.draft?.id ?? null,
    () => {
      void restorePersistedExportRecovery();
    },
    { immediate: true },
  );

  return {
    isBusy,
    statusLabel,
    errorMessage,
    canDownloadLatest,
    startDefaultExport: async () => await startExport("a3_landscape"),
    startExportOption: async (paperSize: SeatingExportPaperSize) => await startExport(paperSize),
    downloadLatest,
  };
}
