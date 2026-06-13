/**
 * Transcript Gateway runtime bridge.
 *
 * Domain purpose:
 *   Submit one authenticated transcript job through HuleEdu Gateway, poll it to
 *   completion, verify the canonical JSON artifact, and support cancellation.
 *
 * Relationships:
 *   - Used by `ConversionHubTranscriptHost`.
 *   - Delegates all Gateway transport to `sirConvertGateway`.
 */

import { onBeforeUnmount, ref } from "vue";

import {
  SIR_CONVERT_ARTIFACT_AVAILABLE,
  isSirConvertGatewayError,
  type SirConvertJobStatus,
  type SirConvertTranscriptArtifactManifest,
  type SirConvertTranscriptJob,
  type SirConvertTranscriptSubmittedJob,
  type SirConvertUploadProgress,
  type TranscriptJson,
  type TranscriptSpeakerControl,
  type TranscriptSubmitParams,
} from "../../../api/sirConvertGateway";

type TranscriptGatewayClient = {
  cancelTranscriptJob(params: { correlationId: string; jobId: string }): Promise<SirConvertTranscriptJob>;
  downloadTranscriptJson(params: { correlationId: string; jobId: string }): Promise<TranscriptJson>;
  getTranscriptJob(params: { correlationId: string; jobId: string }): Promise<SirConvertTranscriptJob>;
  getTranscriptResult(params: {
    correlationId: string;
    jobId: string;
  }): Promise<unknown>;
  listTranscriptArtifacts(params: {
    correlationId: string;
    jobId: string;
  }): Promise<SirConvertTranscriptArtifactManifest>;
  submitTranscriptJob(params: TranscriptSubmitParams): Promise<SirConvertTranscriptSubmittedJob>;
};

export type TranscriptRuntimeStatus = "idle" | "running" | "succeeded" | "failed" | "canceled";

export type TranscriptAbortStatus =
  | "idle"
  | "pending"
  | "accepted"
  | "failed"
  | "rejected"
  | "timed_out";

export type TranscriptAbortState = {
  status: TranscriptAbortStatus;
  message: string | null;
};

export type TranscriptUploadStatus = "idle" | "uploading" | "finalizing";

export type TranscriptUploadState = {
  status: TranscriptUploadStatus;
  loadedBytes: number;
  totalBytes: number | null;
  percentComplete: number | null;
};

export type TranscriptRuntimeSubmission = {
  file: File;
  speakerControl: TranscriptSpeakerControl;
};

export type TranscriptGatewayRuntimeOptions = {
  client?: TranscriptGatewayClient;
  pollIntervalMs?: number;
};

const ACTIVE_STATUSES = new Set<SirConvertJobStatus>([
  "submitted",
  "queued",
  "running",
  "processing",
]);

const DEFAULT_POLL_INTERVAL_MS = 2_000;
const IDLE_ABORT_STATE: TranscriptAbortState = { status: "idle", message: null };
const IDLE_UPLOAD_STATE: TranscriptUploadState = {
  loadedBytes: 0,
  percentComplete: null,
  status: "idle",
  totalBytes: null,
};

const DEFAULT_CLIENT: TranscriptGatewayClient = {
  async cancelTranscriptJob(params) {
    return await (await import("../../../api/sirConvertGateway")).cancelTranscriptJob(params);
  },
  async downloadTranscriptJson(params) {
    return await (await import("../../../api/sirConvertGateway")).downloadTranscriptJson(params);
  },
  async getTranscriptJob(params) {
    return await (await import("../../../api/sirConvertGateway")).getTranscriptJob(params);
  },
  async getTranscriptResult(params) {
    return await (await import("../../../api/sirConvertGateway")).getTranscriptResult(params);
  },
  async listTranscriptArtifacts(params) {
    return await (await import("../../../api/sirConvertGateway")).listTranscriptArtifacts(params);
  },
  async submitTranscriptJob(params) {
    return await (await import("../../../api/sirConvertGateway")).submitTranscriptJob(params);
  },
};

function wait(milliseconds: number): Promise<void> {
  if (milliseconds <= 0) return Promise.resolve();
  return new Promise((resolve) => {
    window.setTimeout(resolve, milliseconds);
  });
}

function isActiveStatus(status: SirConvertJobStatus): boolean {
  return ACTIVE_STATUSES.has(status);
}

function isCanceledStatus(status: SirConvertJobStatus): boolean {
  return status === "canceled" || status === "cancelled";
}

function assertTranscriptJsonAvailable(manifest: SirConvertTranscriptArtifactManifest): void {
  if (manifest.transcriptJsonArtifact?.availability !== SIR_CONVERT_ARTIFACT_AVAILABLE) {
    throw new Error("Transcript JSON is not available.");
  }
}

function abortFailureState(error: unknown): TranscriptAbortState {
  if (isSirConvertGatewayError(error)) {
    if (error.status === 408 || error.code.toLowerCase().includes("timeout")) {
      return {
        status: "timed_out",
        message: "Avbrottet tog för lång tid. Transkriberingen fortsätter.",
      };
    }
    if (error.status >= 400 && error.status < 500) {
      return {
        status: "rejected",
        message: "Avbrottet kunde inte tas emot. Transkriberingen fortsätter.",
      };
    }
  }
  return {
    status: "failed",
    message: "Det gick inte att avbryta. Transkriberingen fortsätter.",
  };
}

export function useTranscriptGatewayRuntime(options: TranscriptGatewayRuntimeOptions = {}) {
  const client = options.client ?? DEFAULT_CLIENT;
  const pollIntervalMs = options.pollIntervalMs ?? DEFAULT_POLL_INTERVAL_MS;
  let activeUploadAbortController: AbortController | null = null;
  const activeRunId = ref(0);
  const status = ref<TranscriptRuntimeStatus>("idle");
  const errorMessage = ref<string | null>(null);
  const transcript = ref<TranscriptJson | null>(null);
  const currentJob = ref<SirConvertTranscriptJob | null>(null);
  const lastCorrelationId = ref<string | null>(null);
  const lastJobId = ref<string | null>(null);
  const abortState = ref<TranscriptAbortState>(IDLE_ABORT_STATE);
  const uploadState = ref<TranscriptUploadState>(IDLE_UPLOAD_STATE);

  function isCurrentRun(runId: number): boolean {
    return activeRunId.value === runId;
  }

  function resetRuntime(): void {
    activeRunId.value += 1;
    status.value = "idle";
    errorMessage.value = null;
    transcript.value = null;
    currentJob.value = null;
    lastCorrelationId.value = null;
    lastJobId.value = null;
    abortState.value = IDLE_ABORT_STATE;
    uploadState.value = IDLE_UPLOAD_STATE;
    activeUploadAbortController?.abort();
    activeUploadAbortController = null;
  }

  function setUploadProgress(progress: SirConvertUploadProgress): void {
    const completed =
      progress.totalBytes !== null && progress.totalBytes > 0 &&
      progress.loadedBytes >= progress.totalBytes;
    uploadState.value = {
      loadedBytes: progress.loadedBytes,
      percentComplete: progress.percentComplete,
      status: completed ? "finalizing" : "uploading",
      totalBytes: progress.totalBytes,
    };
  }

  async function requestGatewayCancel(params: {
    correlationId: string;
    jobId: string;
  }): Promise<boolean> {
    try {
      const canceledJob = await client.cancelTranscriptJob(params);
      currentJob.value = canceledJob;
      if (isCanceledStatus(canceledJob.status)) {
        activeRunId.value += 1;
        status.value = "canceled";
        abortState.value = {
          status: "accepted",
          message: "Transkriberingen är avbruten.",
        };
        return true;
      }
      abortState.value = {
        status: "rejected",
        message: "Avbrottet kunde inte tas emot. Transkriberingen fortsätter.",
      };
      return false;
    } catch (error: unknown) {
      abortState.value = abortFailureState(error);
      return false;
    }
  }

  async function pollToTerminal(
    submittedJob: SirConvertTranscriptSubmittedJob,
    runId: number,
  ): Promise<SirConvertTranscriptJob | null> {
    let job: SirConvertTranscriptJob = submittedJob;
    while (isActiveStatus(job.status)) {
      await wait(pollIntervalMs);
      if (!isCurrentRun(runId)) return null;
      job = await client.getTranscriptJob({
        correlationId: submittedJob.requestContext.correlationId,
        jobId: submittedJob.jobId,
      });
      currentJob.value = job;
    }
    return job;
  }

  async function submitAndPoll(submission: TranscriptRuntimeSubmission): Promise<TranscriptJson | null> {
    const runId = activeRunId.value + 1;
    activeRunId.value = runId;
    status.value = "running";
    errorMessage.value = null;
    transcript.value = null;
    currentJob.value = null;
    lastCorrelationId.value = null;
    lastJobId.value = null;
    abortState.value = IDLE_ABORT_STATE;
    uploadState.value = {
      loadedBytes: 0,
      percentComplete: submission.file.size > 0 ? 0 : null,
      status: "uploading",
      totalBytes: submission.file.size > 0 ? submission.file.size : null,
    };
    activeUploadAbortController = new AbortController();
    try {
      const submittedJob = await client.submitTranscriptJob({
        abortSignal: activeUploadAbortController.signal,
        file: submission.file,
        onUploadProgress: setUploadProgress,
        speakerControl: submission.speakerControl,
        waitSeconds: 0,
      });
      if (!isCurrentRun(runId)) return null;
      activeUploadAbortController = null;
      uploadState.value = IDLE_UPLOAD_STATE;
      currentJob.value = submittedJob;
      lastCorrelationId.value = submittedJob.requestContext.correlationId;
      lastJobId.value = submittedJob.jobId;
      if (abortState.value.status === "pending") {
        const canceled = await requestGatewayCancel({
          correlationId: submittedJob.requestContext.correlationId,
          jobId: submittedJob.jobId,
        });
        if (canceled || !isCurrentRun(runId)) return null;
      }
      const terminalJob = await pollToTerminal(submittedJob, runId);
      if (!terminalJob || !isCurrentRun(runId)) return null;
      if (terminalJob.status !== "succeeded") {
        status.value = isCanceledStatus(terminalJob.status) ? "canceled" : "failed";
        throw new Error("Transcript job did not finish.");
      }
      await client.getTranscriptResult({
        correlationId: submittedJob.requestContext.correlationId,
        jobId: submittedJob.jobId,
      });
      const manifest = await client.listTranscriptArtifacts({
        correlationId: submittedJob.requestContext.correlationId,
        jobId: submittedJob.jobId,
      });
      assertTranscriptJsonAvailable(manifest);
      const transcriptJson = await client.downloadTranscriptJson({
        correlationId: submittedJob.requestContext.correlationId,
        jobId: submittedJob.jobId,
      });
      if (!isCurrentRun(runId)) return null;
      transcript.value = transcriptJson;
      status.value = "succeeded";
      return transcriptJson;
    } catch (error: unknown) {
      activeUploadAbortController = null;
      uploadState.value = IDLE_UPLOAD_STATE;
      if (!isCurrentRun(runId)) return null;
      if (
        status.value === "canceled" &&
        isSirConvertGatewayError(error) &&
        error.code === "SIR_CONVERT_UPLOAD_ABORTED"
      ) {
        return null;
      }
      if (status.value !== "canceled") {
        status.value = "failed";
        errorMessage.value = "Det gick inte att skapa transkriptet. Kontrollera filen och försök igen.";
      }
      throw new Error("Transcript job failed.");
    }
  }

  async function cancelTranscript(): Promise<void> {
    const correlationId = lastCorrelationId.value;
    const jobId = lastJobId.value;
    if (abortState.value.status === "pending") return;
    abortState.value = {
      status: "pending",
      message: "Avbryter transkriberingen.",
    };
    if (!correlationId || !jobId) {
      if (activeUploadAbortController) {
        activeUploadAbortController.abort();
        activeUploadAbortController = null;
        uploadState.value = IDLE_UPLOAD_STATE;
        status.value = "canceled";
        abortState.value = {
          status: "accepted",
          message: "Uppladdningen är avbruten.",
        };
      } else {
        abortState.value = {
          status: "pending",
          message: "Avbryter när transkriberingen har startat.",
        };
      }
      return;
    }
    await requestGatewayCancel({ correlationId, jobId });
  }

  onBeforeUnmount(() => {
    activeRunId.value += 1;
    activeUploadAbortController?.abort();
    activeUploadAbortController = null;
  });

  return {
    abortState,
    cancelTranscript,
    currentJob,
    errorMessage,
    lastCorrelationId,
    lastJobId,
    resetRuntime,
    status,
    submitAndPoll,
    transcript,
    uploadState,
  };
}
