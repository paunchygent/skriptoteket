/**
 * Exam Converter authenticated runtime bridge.
 *
 * Domain purpose:
 *   Submit and poll one authenticated Skriptoteket-owned Exam Converter job.
 *
 * Relationships:
 *   - Used by `ExamConverterAuthenticatedView` after local file intake is valid.
 *   - Uses the local curated-app API while retaining the established UI DTOs.
 *   - Does not render questions, files, reports, downloads, or save actions.
 */

import { onBeforeUnmount, ref } from "vue";

import {
  getLocalExamConversionJob,
  getLocalExamConversionResult,
  getLocalExamConversionSourceState,
  submitLocalExamConversion,
} from "../../../api/examConverterLocal";
import type {
  DigiExamAnswerKeyCompletionMode,
  DigiExamIngestionOverlay,
  DigiExamMigrationTarget,
  ExamAuthoringCorrectionSourceStateIssueResult,
  SirConvertJobStatus,
  SirConvertSubmittedJob,
  SirConvertTerminalResult,
} from "../../../api/sirConvertGateway";
import { DEFAULT_DIGIEXAM_MIGRATION_TARGETS } from "../../../api/sirConvertGateway/jobSpec";

type AuthenticatedRuntimeClient = {
  submitDigiExamMigration: typeof submitLocalExamConversion;
  getDigiExamMigrationJob: typeof getLocalExamConversionJob;
  getDigiExamMigrationResult: typeof getLocalExamConversionResult;
  issueExamAuthoringCorrectionSourceState: typeof getLocalExamConversionSourceState;
};

export type ExamConverterAuthenticatedRuntimeSubmission = {
  sourceFile: File;
  advisoryRetryAttempt?: number | null;
  completionMode?: DigiExamAnswerKeyCompletionMode;
  ingestionOverlay?: DigiExamIngestionOverlay | null;
};

export type ExamConverterAuthenticatedRuntimeOptions = {
  client?: AuthenticatedRuntimeClient;
  pollIntervalMs?: number;
};

const DEFAULT_POLL_INTERVAL_MS = 2_000;
const ACTIVE_JOB_STATUSES = new Set<SirConvertJobStatus>([
  "submitted",
  "queued",
  "running",
  "processing",
]);

const DEFAULT_CLIENT: AuthenticatedRuntimeClient = {
  getDigiExamMigrationJob: getLocalExamConversionJob,
  getDigiExamMigrationResult: getLocalExamConversionResult,
  issueExamAuthoringCorrectionSourceState: getLocalExamConversionSourceState,
  submitDigiExamMigration: submitLocalExamConversion,
};

const EXAM_CONVERTER_JOB_HANDLE_STORAGE_KEY = "skriptoteket.examConverter.jobHandle.v1";

type ExamConverterJobHandle = {
  conversionHubJobId: string;
  correlationId: string;
  inputFilename: string;
  jobId: string;
};

function wait(milliseconds: number): Promise<void> {
  if (milliseconds <= 0) {
    return Promise.resolve();
  }
  return new Promise((resolve) => {
    window.setTimeout(resolve, milliseconds);
  });
}

function isActiveJobStatus(status: SirConvertJobStatus): boolean {
  return ACTIVE_JOB_STATUSES.has(status);
}

function isFailedJobStatus(status: SirConvertJobStatus): boolean {
  return status === "failed" || status === "canceled" || status === "cancelled";
}

function saveJobHandle(handle: ExamConverterJobHandle | null): void {
  try {
    if (handle === null) {
      window.sessionStorage.removeItem(EXAM_CONVERTER_JOB_HANDLE_STORAGE_KEY);
      return;
    }
    window.sessionStorage.setItem(EXAM_CONVERTER_JOB_HANDLE_STORAGE_KEY, JSON.stringify(handle));
  } catch {
    // Session handle persistence is convenience only; durable truth is server-side.
  }
}

function readJobHandle(): ExamConverterJobHandle | null {
  try {
    const raw = window.sessionStorage.getItem(EXAM_CONVERTER_JOB_HANDLE_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<ExamConverterJobHandle>;
    if (
      typeof parsed.conversionHubJobId !== "string" ||
      typeof parsed.correlationId !== "string" ||
      typeof parsed.inputFilename !== "string" ||
      typeof parsed.jobId !== "string"
    ) {
      return null;
    }
    return {
      conversionHubJobId: parsed.conversionHubJobId,
      correlationId: parsed.correlationId,
      inputFilename: parsed.inputFilename,
      jobId: parsed.jobId,
    };
  } catch {
    return null;
  }
}

async function readTerminalResult(params: {
  client: AuthenticatedRuntimeClient;
  correlationId: string;
  jobId: string;
}): Promise<SirConvertTerminalResult> {
  return await params.client.getDigiExamMigrationResult({
    correlationId: params.correlationId,
    jobId: params.jobId,
  });
}

export function useExamConverterAuthenticatedRuntime(
  options: ExamConverterAuthenticatedRuntimeOptions = {},
) {
  const client = options.client ?? DEFAULT_CLIENT;
  const pollIntervalMs = options.pollIntervalMs ?? DEFAULT_POLL_INTERVAL_MS;
  const activeRunId = ref(0);
  const isRuntimeBusy = ref(false);
  const lastConversionHubJobId = ref<string | null>(null);
  const lastCorrelationId = ref<string | null>(null);
  const lastIdempotentReplay = ref<boolean | null>(null);
  const lastJobId = ref<string | null>(null);

  function isCurrentRun(runId: number): boolean {
    return activeRunId.value === runId;
  }

  function cancelRuntime(): void {
    activeRunId.value += 1;
    isRuntimeBusy.value = false;
  }

  function restoreLastJobHandle(): ExamConverterJobHandle | null {
    const handle = readJobHandle();
    if (!handle) return null;
    lastConversionHubJobId.value = handle.conversionHubJobId;
    lastCorrelationId.value = handle.correlationId;
    lastJobId.value = handle.jobId;
    return handle;
  }

  async function pollUntilTerminal(
    submittedJob: SirConvertSubmittedJob,
    runId: number,
  ): Promise<SirConvertTerminalResult | null> {
    let currentStatus = submittedJob.status;

    while (isActiveJobStatus(currentStatus)) {
      await wait(pollIntervalMs);
      if (!isCurrentRun(runId)) {
        return null;
      }
      currentStatus = (
        await client.getDigiExamMigrationJob({
          correlationId: submittedJob.requestContext.correlationId,
          jobId: submittedJob.jobId,
        })
      ).status;
    }

    if (!isCurrentRun(runId)) {
      return null;
    }
    if (currentStatus === "succeeded") {
      return await readTerminalResult({
        client,
        correlationId: submittedJob.requestContext.correlationId,
        jobId: submittedJob.jobId,
      });
    }
    if (isFailedJobStatus(currentStatus)) {
      throw new Error("Exam Converter job did not finish.");
    }
    throw new Error("Exam Converter job returned an unsupported status.");
  }

  async function submitAndPoll(
    submission: ExamConverterAuthenticatedRuntimeSubmission,
  ): Promise<SirConvertTerminalResult | null> {
    const runId = activeRunId.value + 1;
    activeRunId.value = runId;
    isRuntimeBusy.value = true;
    lastCorrelationId.value = null;
    lastConversionHubJobId.value = null;
    lastIdempotentReplay.value = null;
    lastJobId.value = null;
    saveJobHandle(null);

    try {
      const submitParams: Parameters<typeof client.submitDigiExamMigration>[0] = {
        artifactLanguage: "sv",
        completionMode: submission.completionMode,
        file: submission.sourceFile,
        ingestionOverlay: submission.ingestionOverlay,
        targets: [...DEFAULT_DIGIEXAM_MIGRATION_TARGETS] satisfies DigiExamMigrationTarget[],
        waitSeconds: 0,
      };
      if (submission.advisoryRetryAttempt !== null && submission.advisoryRetryAttempt !== undefined) {
        submitParams.advisoryRetryAttempt = submission.advisoryRetryAttempt;
      }
      const submittedJob = await client.submitDigiExamMigration(submitParams);

      if (!isCurrentRun(runId)) {
        return null;
      }

      lastCorrelationId.value = submittedJob.requestContext.correlationId;
      lastIdempotentReplay.value = submittedJob.idempotentReplay;
      lastJobId.value = submittedJob.jobId;
      lastConversionHubJobId.value = submittedJob.jobId;
      saveJobHandle({
        conversionHubJobId: submittedJob.jobId,
        correlationId: submittedJob.requestContext.correlationId,
        inputFilename: submission.sourceFile.name,
        jobId: submittedJob.jobId,
      });
      return await pollUntilTerminal(submittedJob, runId);
    } catch (error) {
      if (!isCurrentRun(runId)) {
        return null;
      }
      throw error;
    } finally {
      if (isCurrentRun(runId)) {
        isRuntimeBusy.value = false;
      }
    }
  }

  async function issueCorrectionSourceState(params: {
    jobId: string;
  }): Promise<ExamAuthoringCorrectionSourceStateIssueResult> {
    const correlationId = lastCorrelationId.value;
    if (!correlationId) {
      throw new Error("Correction source-state issue requires a completed conversion.");
    }
    return await client.issueExamAuthoringCorrectionSourceState({ jobId: params.jobId });
  }

  function clearLastJobHandle(): void {
    lastConversionHubJobId.value = null;
    lastCorrelationId.value = null;
    lastIdempotentReplay.value = null;
    lastJobId.value = null;
    saveJobHandle(null);
  }

  onBeforeUnmount(cancelRuntime);

  return {
    cancelRuntime,
    clearLastJobHandle,
    isRuntimeBusy,
    issueCorrectionSourceState,
    lastConversionHubJobId,
    lastCorrelationId,
    lastIdempotentReplay,
    lastJobId,
    restoreLastJobHandle,
    submitAndPoll,
  };
}
