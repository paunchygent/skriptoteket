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
import { toSirConvertGatewayUrl } from "./urls";
import { prepareDigiExamMigrationRequestContext, stableJsonStringify } from "./requestContext";
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
  SirConvertArtifactBlob,
  SirConvertArtifactManifest,
  SirConvertJob,
  SirConvertSubmittedJob,
  SirConvertTerminalResult,
} from "./types";

export type CsrfTokenProvider = () => Promise<string | null>;

export type SirConvertGatewayClientDependencies = {
  fetcher: typeof fetch;
  ensureCsrfToken: CsrfTokenProvider;
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
};

function buildJsonHeaders(correlationId: string): Headers {
  const headers = new Headers();
  headers.set("Accept", "application/json");
  headers.set("X-Correlation-ID", correlationId);
  return headers;
}

async function buildUnsafeHeaders(params: {
  correlationId: string;
  idempotencyKey: string;
  ensureCsrfToken: CsrfTokenProvider;
}): Promise<Headers> {
  const headers = buildJsonHeaders(params.correlationId);
  headers.set("Idempotency-Key", params.idempotencyKey);
  const csrfToken = await params.ensureCsrfToken();
  if (csrfToken) {
    headers.set("X-CSRF-Token", csrfToken);
  }
  return headers;
}

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

function normalizeWaitSeconds(value: number | undefined): number {
  const waitSeconds = value ?? 0;
  if (!Number.isInteger(waitSeconds) || waitSeconds < 0 || waitSeconds > 20) {
    throw new Error("waitSeconds must be an integer between 0 and 20.");
  }
  return waitSeconds;
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
  };
}

export function createBrowserSirConvertGatewayClient(): SirConvertGatewayClient {
  const auth = useAuthStore();
  return createSirConvertGatewayClient({
    fetcher: (input, init) => fetch(input, init),
    ensureCsrfToken: () => auth.ensureCsrfToken(),
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
