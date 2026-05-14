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
  getDigiExamMigrationJob,
  getDigiExamMigrationResult,
  submitDigiExamMigration,
} from "../../../api/sirConvertGateway";
import type {
  DigiExamMigrationTarget,
  SirConvertJobStatus,
  SirConvertSubmittedJob,
  SirConvertTerminalResult,
} from "../../../api/sirConvertGateway";
import type { ExamConverterTargetSelection } from "./useExamConverterSourceFile";

type AuthenticatedRuntimeClient = {
  submitDigiExamMigration: typeof submitDigiExamMigration;
  getDigiExamMigrationJob: typeof getDigiExamMigrationJob;
  getDigiExamMigrationResult: typeof getDigiExamMigrationResult;
};

export type ExamConverterAuthenticatedRuntimeSubmission = {
  sourceFile: File;
  supportingFile: File | null;
  targetSelection: ExamConverterTargetSelection;
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
  submitDigiExamMigration,
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

function toGatewayTargets(selection: ExamConverterTargetSelection): DigiExamMigrationTarget[] {
  const targets: DigiExamMigrationTarget[] = [];
  if (selection.pdf) {
    targets.push("examnet_pdf");
  }
  if (selection.qti) {
    targets.push("qti_package");
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
  const lastCorrelationId = ref<string | null>(null);
  const lastJobId = ref<string | null>(null);

  function isCurrentRun(runId: number): boolean {
    return activeRunId.value === runId;
  }

  function cancelRuntime(): void {
    activeRunId.value += 1;
    isRuntimeBusy.value = false;
  }

  async function pollUntilTerminal(
    submittedJob: SirConvertSubmittedJob,
    runId: number,
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
      return await readTerminalResult({
        client,
        correlationId,
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
    const targets = toGatewayTargets(submission.targetSelection);
    if (targets.length === 0) {
      throw new Error("At least one target format is required.");
    }

    const runId = activeRunId.value + 1;
    activeRunId.value = runId;
    isRuntimeBusy.value = true;
    lastCorrelationId.value = null;
    lastJobId.value = null;

    try {
      const submittedJob = await client.submitDigiExamMigration({
        artifactLanguage: "sv",
        file: submission.sourceFile,
        gradedResultPdf: submission.supportingFile,
        targets,
        waitSeconds: 0,
      });

      if (!isCurrentRun(runId)) {
        return null;
      }

      lastCorrelationId.value = submittedJob.requestContext.correlationId;
      lastJobId.value = submittedJob.jobId;
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

  onBeforeUnmount(cancelRuntime);

  return {
    cancelRuntime,
    isRuntimeBusy,
    lastCorrelationId,
    lastJobId,
    submitAndPoll,
  };
}
