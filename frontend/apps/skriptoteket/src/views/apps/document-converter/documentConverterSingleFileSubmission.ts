/**
 * Document Converter single-file submission orchestration.
 *
 * Domain purpose:
 *   Convert local-upload or Mina filer source selections into existing
 *   Document Converter jobs, poll them to terminal state, and return
 *   teacher-facing current-result outcomes for the route session.
 *
 * Relationships:
 *   - Called by `useDocumentConverterSingleFile.ts`.
 *   - Uses `documentConverterFileApi.ts` as the protected API boundary.
 *   - Shares source/output labels with `documentConverterSingleFileSelection.ts`.
 */

import type { components } from "../../../api/openapi";
import {
  getDocumentConverterJobStatus,
  submitDocumentConverterSavedFileJob,
  submitDocumentConverterUploadJob,
  type DocumentConverterSavedFileSource,
  type DocumentConverterSingleFileStatusResult,
} from "./documentConverterFileApi";
import {
  OUTPUT_LABELS,
  TERMINAL_STATUSES,
  type DocumentConverterSingleFileOutput,
  type DocumentConverterSingleFileSource,
} from "./documentConverterSingleFileSelection";

type ConversionHubJobStatus = components["schemas"]["ConversionHubJobStatus"];
type StatusMessageSink = (message: string | null) => void;

export type DocumentConverterSingleFileRequest =
  | {
      kind: "upload";
      files: File[];
      outputFormat: DocumentConverterSingleFileOutput;
      sourceFormat: DocumentConverterSingleFileSource;
    }
  | {
      kind: "saved_file";
      outputFormat: DocumentConverterSingleFileOutput;
      savedFiles: DocumentConverterSavedFileSource[];
      sourceFormat: DocumentConverterSingleFileSource;
    };

export type DocumentConverterSingleFileOutcome =
  | {
      type: "ready";
      entryId: string;
      filename: string;
      resultTypeLabel: string;
      sourceLabel: string;
      artifacts: DocumentConverterSingleFileArtifact[];
      request: DocumentConverterSingleFileRequest;
    }
  | {
      type: "failed";
      entryId: string;
      filename: string;
      resultTypeLabel: string;
      sourceLabel: string;
      errorMessage: string;
      request: DocumentConverterSingleFileRequest;
    };

export type DocumentConverterSingleFileArtifact = {
  filename: string;
  jobId: string;
  previewable: boolean;
};

export type DocumentConverterSingleFileSubmissionResult =
  | {
      type: "pending";
      statusMessage: string;
    }
  | {
      type: "outcome";
      outcome: DocumentConverterSingleFileOutcome;
      statusMessage: string | null;
    };

export async function submitDocumentConverterSingleFileRequest(params: {
  request: DocumentConverterSingleFileRequest;
  setStatusMessage: StatusMessageSink;
}): Promise<DocumentConverterSingleFileSubmissionResult> {
  const { request, setStatusMessage } = params;
  setStatusMessage("Startar konverteringen...");
  try {
    const submitResult =
      request.kind === "upload"
        ? await submitDocumentConverterUploadJob({
            files: request.files,
            outputFormat: request.outputFormat,
            sourceFormat: request.sourceFormat,
          })
        : await submitDocumentConverterSavedFileJob({
            outputFormat: request.outputFormat,
            sourceFormat: request.sourceFormat,
            sourceRefs: request.savedFiles.map((file) => file.ref),
          });
    const submittedJobs = submitResult.jobs;
    if (submittedJobs.length === 0) {
      throw new Error("Document Converter did not return a job.");
    }

    const terminalResults = [];
    for (const submittedJob of submittedJobs) {
      terminalResults.push(
        await waitForTerminalJob({
          initialStatus: submittedJob.status,
          jobId: submittedJob.job_id,
          multiFile: submittedJobs.length > 1,
          setStatusMessage,
        }),
      );
    }
    if (terminalResults.some((result) => !TERMINAL_STATUSES.has(result.status))) {
      return {
        type: "pending",
        statusMessage: submittedJobs.length > 1 ? "Arbetar med filerna..." : "Arbetar med filen...",
      };
    }

    const readyArtifacts = terminalResults.flatMap((result) => {
      if (result.status !== "succeeded" || !result.result_artifact) {
        return [];
      }
      const filename = result.result_artifact.filename?.trim();
      if (!filename) {
        return [];
      }
      return [
        {
          filename,
          jobId: result.job_id,
          previewable: result.result_artifact.content_type === "application/pdf",
        },
      ];
    });
    const sourceLabel = request.kind === "upload" ? "Lokal fil" : "Mina filer";
    if (readyArtifacts.length === terminalResults.length) {
      return {
        type: "outcome",
        outcome: {
          type: "ready",
          artifacts: readyArtifacts,
          entryId: `job:${terminalResults.map((result) => result.job_id).join(":")}`,
          filename:
            readyArtifacts.length === 1
              ? readyArtifacts[0]?.filename ?? submittedJobs[0]?.input_filename ?? "Resultat"
              : `${readyArtifacts.length.toLocaleString("sv-SE")} ${
                  OUTPUT_LABELS[request.outputFormat]
                }-filer`,
          request,
          resultTypeLabel: OUTPUT_LABELS[request.outputFormat],
          sourceLabel,
        },
        statusMessage: null,
      };
    }

    return {
      type: "outcome",
      outcome: {
        type: "failed",
        entryId: `job:${terminalResults.map((result) => result.job_id).join(":")}:failed`,
        errorMessage:
          terminalResults.find((result) => result.error)?.error ??
          submittedJobs.find((job) => job.error)?.error ??
          "Konverteringen kunde inte slutföras.",
        filename: submittedJobs[0]?.input_filename ?? "Resultat",
        request,
        resultTypeLabel: OUTPUT_LABELS[request.outputFormat],
        sourceLabel,
      },
      statusMessage: null,
    };
  } catch {
    return {
      type: "outcome",
      outcome: {
        type: "failed",
        entryId: `job:failed:${Date.now()}`,
        errorMessage: "Konverteringen kunde inte starta.",
        filename:
          request.kind === "upload"
            ? request.files[0]?.name ?? "Resultat"
            : request.savedFiles[0]?.name ?? "Resultat",
        request,
        resultTypeLabel: OUTPUT_LABELS[request.outputFormat],
        sourceLabel: request.kind === "upload" ? "Lokal fil" : "Mina filer",
      },
      statusMessage: null,
    };
  }
}

async function waitForTerminalJob(params: {
  initialStatus: ConversionHubJobStatus;
  jobId: string;
  multiFile: boolean;
  setStatusMessage: StatusMessageSink;
}): Promise<DocumentConverterSingleFileStatusResult> {
  if (TERMINAL_STATUSES.has(params.initialStatus)) {
    return await getDocumentConverterJobStatus({ jobId: params.jobId });
  }

  let attempts = 0;
  let currentStatus = params.initialStatus;
  let currentResult: DocumentConverterSingleFileStatusResult = {
    error: null,
    job_id: params.jobId,
    result_artifact: null,
    status: currentStatus,
  };

  while (!TERMINAL_STATUSES.has(currentStatus) && attempts < 20) {
    params.setStatusMessage(params.multiFile ? "Arbetar med filerna..." : "Arbetar med filen...");
    await new Promise<void>((resolve) => window.setTimeout(resolve, 1000));
    currentResult = await getDocumentConverterJobStatus({ jobId: params.jobId });
    currentStatus = currentResult.status;
    attempts += 1;
  }

  if (currentResult.job_id !== params.jobId || currentResult.status !== currentStatus) {
    currentResult = await getDocumentConverterJobStatus({ jobId: params.jobId });
  }
  return currentResult;
}
