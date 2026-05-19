/**
 * Exam Converter authenticated runtime bridge.
 *
 * Domain purpose:
 *   Submit one authenticated Exam Converter job through the HuleEdu Gateway and
 *   poll it to the terminal Sir Convert result consumed by the UI result strip.
 *
 * Relationships:
 *   - Used by `ExamConverterAuthenticatedView` after local file intake is valid.
 *   - Delegates transport, CSRF, idempotency, and correlation headers to the
 *     existing Sir Convert Gateway client.
 *   - Does not render questions, files, reports, downloads, or save actions.
 */

import { onBeforeUnmount, ref } from "vue";

import {
  registerExamConverterConversionHubJob,
  type RegisterExamConverterConversionHubJobRequest,
  type RegisterExamConverterConversionHubJobResult,
} from "../../../api/examConverterCorrectionSessions";
import {
  applyExamAuthoringCorrections,
  getDigiExamMigrationJob,
  getDigiExamMigrationResult,
  issueExamAuthoringCorrectionSourceState,
  submitDigiExamMigration,
} from "../../../api/sirConvertGateway";
import type {
  DigiExamAnswerKeyCompletionMode,
  DigiExamIngestionOverlay,
  DigiExamMigrationTarget,
  ExamAuthoringCorrectionSourceStateIssueResult,
  ExamAuthoringCorrectionsApplyRequest,
  ExamAuthoringCorrectionsApplyResult,
  SirConvertJobStatus,
  SirConvertSubmittedJob,
  SirConvertTerminalResult,
} from "../../../api/sirConvertGateway";
import {
  DIGIEXAM_TARGET_EXAMNET_PDF,
  DIGIEXAM_TARGET_QTI_PACKAGE,
} from "../../../api/sirConvertGateway/contractValues";
import type { ExamConverterTargetSelection } from "./useExamConverterSourceFile";

type AuthenticatedRuntimeClient = {
  submitDigiExamMigration: typeof submitDigiExamMigration;
  getDigiExamMigrationJob: typeof getDigiExamMigrationJob;
  getDigiExamMigrationResult: typeof getDigiExamMigrationResult;
  issueExamAuthoringCorrectionSourceState: typeof issueExamAuthoringCorrectionSourceState;
  applyExamAuthoringCorrections: typeof applyExamAuthoringCorrections;
  registerExamConverterConversionHubJob: typeof registerExamConverterConversionHubJob;
};

export type ExamConverterAuthenticatedRuntimeSubmission = {
  sourceFile: File;
  supportingFile: File | null;
  targetSelection: ExamConverterTargetSelection;
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
  getDigiExamMigrationJob,
  getDigiExamMigrationResult,
  issueExamAuthoringCorrectionSourceState,
  applyExamAuthoringCorrections,
  registerExamConverterConversionHubJob,
  submitDigiExamMigration,
};

const EXAM_CONVERTER_JOB_HANDLE_STORAGE_KEY = "skriptoteket.examConverter.jobHandle.v1";

type ExamConverterJobHandle = {
  conversionHubJobId: string;
  correlationId: string;
  inputFilename: string;
  sirConvertJobId: string;
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

function toRegisteredJobStatus(
  status: SirConvertJobStatus,
): RegisterExamConverterConversionHubJobRequest["status"] {
  if (status === "running") return "processing";
  if (status === "cancelled") return "canceled";
  if (status === "succeeded" || status === "failed" || status === "submitted") return status;
  if (status === "queued" || status === "processing" || status === "canceled") return status;
  return "processing";
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
      typeof parsed.sirConvertJobId !== "string"
    ) {
      return null;
    }
    return {
      conversionHubJobId: parsed.conversionHubJobId,
      correlationId: parsed.correlationId,
      inputFilename: parsed.inputFilename,
      sirConvertJobId: parsed.sirConvertJobId,
    };
  } catch {
    return null;
  }
}

function toGatewayTargets(selection: ExamConverterTargetSelection): DigiExamMigrationTarget[] {
  const targets: DigiExamMigrationTarget[] = [];
  if (selection.pdf) {
    targets.push(DIGIEXAM_TARGET_EXAMNET_PDF);
  }
  if (selection.qti) {
    targets.push(DIGIEXAM_TARGET_QTI_PACKAGE);
  }
  return targets;
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
    lastJobId.value = handle.sirConvertJobId;
    return handle;
  }

  async function registerLocalJob(params: {
    correlationId: string;
    inputFilename: string;
    status: RegisterExamConverterConversionHubJobRequest["status"];
    upstreamJobId: string;
  }): Promise<RegisterExamConverterConversionHubJobResult> {
    return await client.registerExamConverterConversionHubJob({
      request: {
        correlation_id: params.correlationId,
        input_filename: params.inputFilename,
        status: params.status,
        upstream_job_id: params.upstreamJobId,
      },
    });
  }

  async function pollUntilTerminal(
    submittedJob: SirConvertSubmittedJob,
    runId: number,
    synchronizeTerminalStatus: (status: SirConvertJobStatus) => Promise<void>,
  ): Promise<SirConvertTerminalResult | null> {
    const correlationId = submittedJob.requestContext.correlationId;
    let currentStatus = submittedJob.status;

    while (isActiveJobStatus(currentStatus)) {
      await wait(pollIntervalMs);
      if (!isCurrentRun(runId)) {
        return null;
      }
      currentStatus = (
        await client.getDigiExamMigrationJob({
          correlationId,
          jobId: submittedJob.jobId,
        })
      ).status;
    }

    if (!isCurrentRun(runId)) {
      return null;
    }
    if (currentStatus === "succeeded") {
      await synchronizeTerminalStatus(currentStatus);
      return await readTerminalResult({
        client,
        correlationId,
        jobId: submittedJob.jobId,
      });
    }
    if (isFailedJobStatus(currentStatus)) {
      await synchronizeTerminalStatus(currentStatus);
      throw new Error("Exam Converter job did not finish.");
    }
    throw new Error("Exam Converter job returned an unsupported status.");
  }

  async function submitAndPoll(
    submission: ExamConverterAuthenticatedRuntimeSubmission,
  ): Promise<SirConvertTerminalResult | null> {
    const targets = toGatewayTargets(submission.targetSelection);
    if (targets.length === 0) {
      throw new Error("At least one target format is required.");
    }

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
        gradedResultPdf: submission.supportingFile,
        ingestionOverlay: submission.ingestionOverlay,
        targets,
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
      let lastRegisteredStatus = toRegisteredJobStatus(submittedJob.status);
      const registeredJob = await registerLocalJob({
        correlationId: submittedJob.requestContext.correlationId,
        inputFilename: submission.sourceFile.name,
        status: lastRegisteredStatus,
        upstreamJobId: submittedJob.jobId,
      });
      lastConversionHubJobId.value = registeredJob.job_id;
      saveJobHandle({
        conversionHubJobId: registeredJob.job_id,
        correlationId: submittedJob.requestContext.correlationId,
        inputFilename: submission.sourceFile.name,
        sirConvertJobId: submittedJob.jobId,
      });
      return await pollUntilTerminal(submittedJob, runId, async (status) => {
        const nextRegisteredStatus = toRegisteredJobStatus(status);
        if (nextRegisteredStatus === lastRegisteredStatus) {
          return;
        }
        lastRegisteredStatus = nextRegisteredStatus;
        const synchronizedJob = await registerLocalJob({
          correlationId: submittedJob.requestContext.correlationId,
          inputFilename: submission.sourceFile.name,
          status: nextRegisteredStatus,
          upstreamJobId: submittedJob.jobId,
        });
        lastConversionHubJobId.value = synchronizedJob.job_id;
      });
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
    return await client.issueExamAuthoringCorrectionSourceState({
      correlationId,
      request: {
        schema_version: "exam_authoring_correction_source_state_issue_request_v1",
        job_id: params.jobId,
      },
    });
  }

  async function applyCorrectionRequest(
    request: ExamAuthoringCorrectionsApplyRequest,
  ): Promise<ExamAuthoringCorrectionsApplyResult> {
    const correlationId = lastCorrelationId.value;
    if (!correlationId) {
      throw new Error("Correction apply requires a completed conversion.");
    }
    return await client.applyExamAuthoringCorrections({ correlationId, request });
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
    applyCorrectionRequest,
    restoreLastJobHandle,
    submitAndPoll,
  };
}
