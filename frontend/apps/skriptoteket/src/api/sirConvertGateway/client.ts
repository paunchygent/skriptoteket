/**
 * Sir Convert Gateway transport client.
 *
 * Purpose:
 *   Execute authenticated browser-session calls against HuleEdu's
 *   `/sir-convert/v2/convert` edge while keeping conversion semantics in Sir
 *   Convert and UI orchestration outside the transport layer.
 *
 * Relationships:
 *   - `requestContext.ts` prepares deterministic headers and JobSpec JSON.
 *   - `parsers.ts` validates all returned Sir Convert envelopes.
 */

import { useAuthStore } from "../../stores/auth";
import { DIGIEXAM_INGESTION_OVERLAY_FILENAME } from "./contractValues";
import { toSirConvertGatewayProductUrl, toSirConvertGatewayUrl } from "./urls";
import { prepareDigiExamMigrationRequestContext, stableJsonStringify } from "./requestContext";
import { prepareTranscriptRequestContext } from "./transcriptRequestContext";
import {
  parseArtifactManifest,
  parseContentDispositionFilename,
  parseJob,
  parseTerminalResult,
  readJsonOrThrow,
  toGatewayError,
} from "./parsers";
import type {
  DigiExamMigrationSubmitParams,
  ExamAuthoringCorrectionSourceStateIssueRequest,
  ExamAuthoringCorrectionSourceStateIssueResult,
  ExamAuthoringCorrectionsApplyRequest,
  ExamAuthoringCorrectionsApplyResult,
  SirConvertArtifactBlob,
  SirConvertArtifactManifest,
  SirConvertJob,
  SirConvertSubmittedJob,
  SirConvertTerminalResult,
} from "./types";
import {
  parseTranscriptArtifactManifest,
  parseTranscriptJob,
  parseTranscriptJson,
  parseTranscriptResult,
} from "./transcriptParsers";
import {
  buildJsonHeaders,
  buildUnsafeActionHeaders,
  buildUnsafeHeaders,
  buildUnsafeJsonHeaders,
  normalizeWaitSeconds,
  type CsrfTokenProvider,
} from "./headers";
import {
  browserMultipartUploadTransport,
  type SirConvertMultipartUploadTransport,
} from "./multipartUploadTransport";
import type {
  SirConvertTranscriptArtifactManifest,
  SirConvertTranscriptCancelResult,
  SirConvertTranscriptJob,
  SirConvertTranscriptSubmittedJob,
  SirConvertTranscriptTerminalResult,
  TranscriptJson,
  TranscriptSubmitParams,
} from "./transcriptTypes";

export type SirConvertGatewayClientDependencies = {
  fetcher: typeof fetch;
  ensureCsrfToken: CsrfTokenProvider;
  multipartUploadTransport?: SirConvertMultipartUploadTransport;
};

export type SirConvertGatewayClient = {
  submitDigiExamMigration(params: DigiExamMigrationSubmitParams): Promise<SirConvertSubmittedJob>;
  getDigiExamMigrationJob(params: {
    jobId: string;
    correlationId: string;
  }): Promise<SirConvertJob>;
  getDigiExamMigrationResult(params: {
    jobId: string;
    correlationId: string;
  }): Promise<SirConvertTerminalResult>;
  listDigiExamMigrationArtifacts(params: {
    jobId: string;
    correlationId: string;
  }): Promise<SirConvertArtifactManifest>;
  downloadDigiExamMigrationArtifact(params: {
    jobId: string;
    artifactKey: string;
    correlationId: string;
  }): Promise<SirConvertArtifactBlob>;
  submitTranscriptJob(params: TranscriptSubmitParams): Promise<SirConvertTranscriptSubmittedJob>;
  getTranscriptJob(params: {
    jobId: string;
    correlationId: string;
  }): Promise<SirConvertTranscriptJob>;
  getTranscriptResult(params: {
    jobId: string;
    correlationId: string;
  }): Promise<SirConvertTranscriptTerminalResult>;
  listTranscriptArtifacts(params: {
    jobId: string;
    correlationId: string;
  }): Promise<SirConvertTranscriptArtifactManifest>;
  downloadTranscriptJson(params: {
    jobId: string;
    correlationId: string;
  }): Promise<TranscriptJson>;
  cancelTranscriptJob(params: {
    jobId: string;
    correlationId: string;
  }): Promise<SirConvertTranscriptCancelResult>;
  issueExamAuthoringCorrectionSourceState(params: {
    correlationId: string;
    request: ExamAuthoringCorrectionSourceStateIssueRequest;
  }): Promise<ExamAuthoringCorrectionSourceStateIssueResult>;
  applyExamAuthoringCorrections(params: {
    correlationId: string;
    request: ExamAuthoringCorrectionsApplyRequest;
  }): Promise<ExamAuthoringCorrectionsApplyResult>;
};

function appendOptionalFile(
  formData: FormData,
  fieldName: string,
  file: File | null | undefined,
): void {
  if (file) {
    formData.append(fieldName, file, file.name);
  }
}

function appendOptionalIngestionOverlay(
  formData: FormData,
  overlay: DigiExamMigrationSubmitParams["ingestionOverlay"],
): void {
  if (!overlay) return;
  formData.append(
    "digiexam_ingestion_overlay",
    new Blob([stableJsonStringify(overlay)], { type: "application/json" }),
    DIGIEXAM_INGESTION_OVERLAY_FILENAME,
  );
}

export function createSirConvertGatewayClient(
  dependencies: SirConvertGatewayClientDependencies,
): SirConvertGatewayClient {
  return {
    async submitDigiExamMigration(params) {
      const requestContext = await prepareDigiExamMigrationRequestContext(params);
      const formData = new FormData();
      formData.append("file", params.file, params.file.name);
      appendOptionalFile(formData, "graded_result_pdf", params.gradedResultPdf);
      appendOptionalFile(formData, "parity_pdf", params.parityPdf);
      appendOptionalIngestionOverlay(formData, params.ingestionOverlay);
      formData.append("job_spec", stableJsonStringify(requestContext.jobSpec));

      const response = await dependencies.fetcher(
        toSirConvertGatewayUrl(`/jobs?wait_seconds=${normalizeWaitSeconds(params.waitSeconds)}`),
        {
          method: "POST",
          headers: await buildUnsafeHeaders({
            correlationId: requestContext.correlationId,
            idempotencyKey: requestContext.idempotencyKey,
            ensureCsrfToken: dependencies.ensureCsrfToken,
          }),
          body: formData,
          credentials: "include",
        },
      );
      const submitted = await readJsonOrThrow(response, parseJob);
      return {
        ...submitted,
        idempotentReplay: response.headers.get("X-Idempotent-Replay")?.toLowerCase() === "true",
        requestContext,
      };
    },

    async getDigiExamMigrationJob(params) {
      const response = await dependencies.fetcher(toSirConvertGatewayUrl(`/jobs/${params.jobId}`), {
        method: "GET",
        headers: buildJsonHeaders(params.correlationId),
        credentials: "include",
      });
      return await readJsonOrThrow(response, parseJob);
    },

    async getDigiExamMigrationResult(params) {
      const response = await dependencies.fetcher(
        toSirConvertGatewayUrl(`/jobs/${params.jobId}/result`),
        {
          method: "GET",
          headers: buildJsonHeaders(params.correlationId),
          credentials: "include",
        },
      );
      return await readJsonOrThrow(response, parseTerminalResult);
    },

    async listDigiExamMigrationArtifacts(params) {
      const response = await dependencies.fetcher(
        toSirConvertGatewayUrl(`/jobs/${params.jobId}/artifacts`),
        {
          method: "GET",
          headers: buildJsonHeaders(params.correlationId),
          credentials: "include",
        },
      );
      return await readJsonOrThrow(response, parseArtifactManifest);
    },

    async downloadDigiExamMigrationArtifact(params) {
      const response = await dependencies.fetcher(
        toSirConvertGatewayUrl(`/jobs/${params.jobId}/artifacts/${params.artifactKey}`),
        {
          method: "GET",
          headers: buildJsonHeaders(params.correlationId),
          credentials: "include",
        },
      );
      if (!response.ok) {
        throw await toGatewayError(response);
      }
      return {
        blob: await response.blob(),
        contentType: response.headers.get("content-type"),
        filename: parseContentDispositionFilename(response.headers.get("content-disposition")),
        artifactKey: params.artifactKey,
      };
    },

    async submitTranscriptJob(params) {
      const requestContext = await prepareTranscriptRequestContext(params);
      const formData = new FormData();
      formData.append("file", params.file, params.file.name);
      formData.append("job_spec", stableJsonStringify(requestContext.jobSpec));
      const url = toSirConvertGatewayUrl(
        `/jobs?wait_seconds=${normalizeWaitSeconds(params.waitSeconds)}`,
      );
      const headers = await buildUnsafeHeaders({
        correlationId: requestContext.correlationId,
        idempotencyKey: requestContext.idempotencyKey,
        ensureCsrfToken: dependencies.ensureCsrfToken,
      });

      const response =
        params.onUploadProgress || params.abortSignal
          ? await (dependencies.multipartUploadTransport ?? browserMultipartUploadTransport)({
              body: formData,
              credentials: "include",
              headers,
              method: "POST",
              onUploadProgress: params.onUploadProgress,
              signal: params.abortSignal,
              url,
            })
          : await dependencies.fetcher(url, {
              method: "POST",
              headers,
              body: formData,
              credentials: "include",
            });
      const submitted = await readJsonOrThrow(response, parseTranscriptJob);
      return {
        ...submitted,
        idempotentReplay: response.headers.get("X-Idempotent-Replay")?.toLowerCase() === "true",
        requestContext,
      };
    },

    async getTranscriptJob(params) {
      const response = await dependencies.fetcher(toSirConvertGatewayUrl(`/jobs/${params.jobId}`), {
        method: "GET",
        headers: buildJsonHeaders(params.correlationId),
        credentials: "include",
      });
      return await readJsonOrThrow(response, parseTranscriptJob);
    },

    async getTranscriptResult(params) {
      const response = await dependencies.fetcher(
        toSirConvertGatewayUrl(`/jobs/${params.jobId}/result`),
        {
          method: "GET",
          headers: buildJsonHeaders(params.correlationId),
          credentials: "include",
        },
      );
      return await readJsonOrThrow(response, parseTranscriptResult);
    },

    async listTranscriptArtifacts(params) {
      const response = await dependencies.fetcher(
        toSirConvertGatewayUrl(`/jobs/${params.jobId}/artifacts`),
        {
          method: "GET",
          headers: buildJsonHeaders(params.correlationId),
          credentials: "include",
        },
      );
      return await readJsonOrThrow(response, parseTranscriptArtifactManifest);
    },

    async downloadTranscriptJson(params) {
      const response = await dependencies.fetcher(
        toSirConvertGatewayUrl(`/jobs/${params.jobId}/artifacts/transcript_json`),
        {
          method: "GET",
          headers: buildJsonHeaders(params.correlationId),
          credentials: "include",
        },
      );
      return await readJsonOrThrow(response, parseTranscriptJson);
    },

    async cancelTranscriptJob(params) {
      const response = await dependencies.fetcher(
        toSirConvertGatewayUrl(`/jobs/${params.jobId}/cancel`),
        {
          method: "POST",
          headers: await buildUnsafeActionHeaders({
            correlationId: params.correlationId,
            ensureCsrfToken: dependencies.ensureCsrfToken,
          }),
          credentials: "include",
        },
      );
      return await readJsonOrThrow(response, parseTranscriptJob);
    },

    async issueExamAuthoringCorrectionSourceState(params) {
      const response = await dependencies.fetcher(
        toSirConvertGatewayProductUrl("/exam-authoring/corrections/source-state/issue"),
        {
          method: "POST",
          headers: await buildUnsafeJsonHeaders({
            correlationId: params.correlationId,
            ensureCsrfToken: dependencies.ensureCsrfToken,
          }),
          body: stableJsonStringify(params.request),
          credentials: "include",
        },
      );
      return await readJsonOrThrow(
        response,
        (payload) => payload as ExamAuthoringCorrectionSourceStateIssueResult,
      );
    },

    async applyExamAuthoringCorrections(params) {
      const response = await dependencies.fetcher(
        toSirConvertGatewayProductUrl("/exam-authoring/corrections/apply"),
        {
          method: "POST",
          headers: await buildUnsafeJsonHeaders({
            correlationId: params.correlationId,
            ensureCsrfToken: dependencies.ensureCsrfToken,
          }),
          body: stableJsonStringify(params.request),
          credentials: "include",
        },
      );
      return await readJsonOrThrow(
        response,
        (payload) => payload as ExamAuthoringCorrectionsApplyResult,
      );
    },
  };
}

export function createBrowserSirConvertGatewayClient(): SirConvertGatewayClient {
  const auth = useAuthStore();
  return createSirConvertGatewayClient({
    fetcher: (input, init) => fetch(input, init),
    ensureCsrfToken: () => auth.ensureCsrfToken(),
    multipartUploadTransport: browserMultipartUploadTransport,
  });
}

export async function submitDigiExamMigration(
  params: DigiExamMigrationSubmitParams,
): Promise<SirConvertSubmittedJob> {
  return await createBrowserSirConvertGatewayClient().submitDigiExamMigration(params);
}

export async function getDigiExamMigrationJob(params: {
  jobId: string;
  correlationId: string;
}): Promise<SirConvertJob> {
  return await createBrowserSirConvertGatewayClient().getDigiExamMigrationJob(params);
}

export async function getDigiExamMigrationResult(params: {
  jobId: string;
  correlationId: string;
}): Promise<SirConvertTerminalResult> {
  return await createBrowserSirConvertGatewayClient().getDigiExamMigrationResult(params);
}

export async function listDigiExamMigrationArtifacts(params: {
  jobId: string;
  correlationId: string;
}): Promise<SirConvertArtifactManifest> {
  return await createBrowserSirConvertGatewayClient().listDigiExamMigrationArtifacts(params);
}

export async function downloadDigiExamMigrationArtifact(params: {
  jobId: string;
  artifactKey: string;
  correlationId: string;
}): Promise<SirConvertArtifactBlob> {
  return await createBrowserSirConvertGatewayClient().downloadDigiExamMigrationArtifact(params);
}

export async function submitTranscriptJob(
  params: TranscriptSubmitParams,
): Promise<SirConvertTranscriptSubmittedJob> {
  return await createBrowserSirConvertGatewayClient().submitTranscriptJob(params);
}

export async function getTranscriptJob(params: {
  jobId: string;
  correlationId: string;
}): Promise<SirConvertTranscriptJob> {
  return await createBrowserSirConvertGatewayClient().getTranscriptJob(params);
}

export async function getTranscriptResult(params: {
  jobId: string;
  correlationId: string;
}): Promise<SirConvertTranscriptTerminalResult> {
  return await createBrowserSirConvertGatewayClient().getTranscriptResult(params);
}

export async function listTranscriptArtifacts(params: {
  jobId: string;
  correlationId: string;
}): Promise<SirConvertTranscriptArtifactManifest> {
  return await createBrowserSirConvertGatewayClient().listTranscriptArtifacts(params);
}

export async function downloadTranscriptJson(params: {
  jobId: string;
  correlationId: string;
}): Promise<TranscriptJson> {
  return await createBrowserSirConvertGatewayClient().downloadTranscriptJson(params);
}

export async function cancelTranscriptJob(params: {
  jobId: string;
  correlationId: string;
}): Promise<SirConvertTranscriptCancelResult> {
  return await createBrowserSirConvertGatewayClient().cancelTranscriptJob(params);
}

export async function issueExamAuthoringCorrectionSourceState(params: {
  correlationId: string;
  request: ExamAuthoringCorrectionSourceStateIssueRequest;
}): Promise<ExamAuthoringCorrectionSourceStateIssueResult> {
  return await createBrowserSirConvertGatewayClient().issueExamAuthoringCorrectionSourceState(params);
}

export async function applyExamAuthoringCorrections(params: {
  correlationId: string;
  request: ExamAuthoringCorrectionsApplyRequest;
}): Promise<ExamAuthoringCorrectionsApplyResult> {
  return await createBrowserSirConvertGatewayClient().applyExamAuthoringCorrections(params);
}
