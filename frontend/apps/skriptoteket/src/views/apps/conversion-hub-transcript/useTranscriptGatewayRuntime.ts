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
  type SirConvertJobStatus,
  type SirConvertTranscriptArtifactManifest,
  type SirConvertTranscriptJob,
  type SirConvertTranscriptSubmittedJob,
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

export function useTranscriptGatewayRuntime(options: TranscriptGatewayRuntimeOptions = {}) {
  const client = options.client ?? DEFAULT_CLIENT;
  const pollIntervalMs = options.pollIntervalMs ?? DEFAULT_POLL_INTERVAL_MS;
  const activeRunId = ref(0);
  const status = ref<TranscriptRuntimeStatus>("idle");
  const errorMessage = ref<string | null>(null);
  const transcript = ref<TranscriptJson | null>(null);
  const currentJob = ref<SirConvertTranscriptJob | null>(null);
  const lastCorrelationId = ref<string | null>(null);
  const lastJobId = ref<string | null>(null);

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
    try {
      const submittedJob = await client.submitTranscriptJob({
        file: submission.file,
        speakerControl: submission.speakerControl,
        waitSeconds: 0,
      });
      if (!isCurrentRun(runId)) return null;
      currentJob.value = submittedJob;
      lastCorrelationId.value = submittedJob.requestContext.correlationId;
      lastJobId.value = submittedJob.jobId;
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
    } catch {
      if (isCurrentRun(runId) && status.value !== "canceled") {
        status.value = "failed";
        errorMessage.value = "Det gick inte att skapa transkriptet. Kontrollera filen och försök igen.";
      }
      throw new Error("Transcript job failed.");
    }
  }

  async function cancelTranscript(): Promise<void> {
    const correlationId = lastCorrelationId.value;
    const jobId = lastJobId.value;
    activeRunId.value += 1;
    if (!correlationId || !jobId) {
      status.value = "canceled";
      return;
    }
    currentJob.value = await client.cancelTranscriptJob({ correlationId, jobId });
    status.value = "canceled";
  }

  onBeforeUnmount(() => {
    activeRunId.value += 1;
  });

  return {
    cancelTranscript,
    currentJob,
    errorMessage,
    lastCorrelationId,
    lastJobId,
    resetRuntime,
    status,
    submitAndPoll,
    transcript,
  };
}
