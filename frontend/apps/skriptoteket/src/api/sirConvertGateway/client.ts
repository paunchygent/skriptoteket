/** Authenticated Sir Convert Gateway transport for transcript conversion only. */

import { useAuthStore } from "../../stores/auth";
import { toSirConvertGatewayUrl } from "./urls";
import { stableJsonStringify } from "./requestFingerprint";
import { prepareTranscriptRequestContext } from "./transcriptRequestContext";
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
  normalizeWaitSeconds,
  type CsrfTokenProvider,
} from "./headers";
import {
  browserMultipartUploadTransport,
  type SirConvertMultipartUploadTransport,
} from "./multipartUploadTransport";
import { readJsonOrThrow } from "./parsers";
import type {
  SirConvertTranscriptArtifactManifest,
  SirConvertTranscriptCancelResult,
  SirConvertTranscriptJob,
  SirConvertTranscriptSubmittedJob,
  SirConvertTranscriptTerminalResult,
  TranscriptJson,
  TranscriptSubmitParams,
} from "./transcriptTypes";

export type SirConvertTranscriptGatewayClientDependencies = {
  fetcher: typeof fetch;
  ensureCsrfToken: CsrfTokenProvider;
  multipartUploadTransport?: SirConvertMultipartUploadTransport;
};

export type SirConvertTranscriptGatewayClient = {
  submitTranscriptJob(params: TranscriptSubmitParams): Promise<SirConvertTranscriptSubmittedJob>;
  getTranscriptJob(params: { jobId: string; correlationId: string }): Promise<SirConvertTranscriptJob>;
  getTranscriptResult(params: { jobId: string; correlationId: string }): Promise<SirConvertTranscriptTerminalResult>;
  listTranscriptArtifacts(params: { jobId: string; correlationId: string }): Promise<SirConvertTranscriptArtifactManifest>;
  downloadTranscriptJson(params: { jobId: string; correlationId: string }): Promise<TranscriptJson>;
  cancelTranscriptJob(params: { jobId: string; correlationId: string }): Promise<SirConvertTranscriptCancelResult>;
};

export function createSirConvertTranscriptGatewayClient(
  dependencies: SirConvertTranscriptGatewayClientDependencies,
): SirConvertTranscriptGatewayClient {
  return {
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
          : await dependencies.fetcher(url, { body: formData, credentials: "include", headers, method: "POST" });
      const submitted = await readJsonOrThrow(response, parseTranscriptJob);
      return {
        ...submitted,
        idempotentReplay: response.headers.get("X-Idempotent-Replay")?.toLowerCase() === "true",
        requestContext,
      };
    },
    async getTranscriptJob(params) {
      const response = await dependencies.fetcher(toSirConvertGatewayUrl(`/jobs/${params.jobId}`), {
        credentials: "include", headers: buildJsonHeaders(params.correlationId), method: "GET",
      });
      return await readJsonOrThrow(response, parseTranscriptJob);
    },
    async getTranscriptResult(params) {
      const response = await dependencies.fetcher(toSirConvertGatewayUrl(`/jobs/${params.jobId}/result`), {
        credentials: "include", headers: buildJsonHeaders(params.correlationId), method: "GET",
      });
      return await readJsonOrThrow(response, parseTranscriptResult);
    },
    async listTranscriptArtifacts(params) {
      const response = await dependencies.fetcher(toSirConvertGatewayUrl(`/jobs/${params.jobId}/artifacts`), {
        credentials: "include", headers: buildJsonHeaders(params.correlationId), method: "GET",
      });
      return await readJsonOrThrow(response, parseTranscriptArtifactManifest);
    },
    async downloadTranscriptJson(params) {
      const response = await dependencies.fetcher(toSirConvertGatewayUrl(`/jobs/${params.jobId}/artifacts/transcript_json`), {
        credentials: "include", headers: buildJsonHeaders(params.correlationId), method: "GET",
      });
      return await readJsonOrThrow(response, parseTranscriptJson);
    },
    async cancelTranscriptJob(params) {
      const response = await dependencies.fetcher(toSirConvertGatewayUrl(`/jobs/${params.jobId}/cancel`), {
        credentials: "include",
        headers: await buildUnsafeActionHeaders({ correlationId: params.correlationId, ensureCsrfToken: dependencies.ensureCsrfToken }),
        method: "POST",
      });
      return await readJsonOrThrow(response, parseTranscriptJob);
    },
  };
}

function createBrowserSirConvertTranscriptGatewayClient(): SirConvertTranscriptGatewayClient {
  const auth = useAuthStore();
  return createSirConvertTranscriptGatewayClient({
    ensureCsrfToken: () => auth.ensureCsrfToken(),
    fetcher: (input, init) => fetch(input, init),
    multipartUploadTransport: browserMultipartUploadTransport,
  });
}

export async function submitTranscriptJob(params: TranscriptSubmitParams): Promise<SirConvertTranscriptSubmittedJob> {
  return await createBrowserSirConvertTranscriptGatewayClient().submitTranscriptJob(params);
}

export async function getTranscriptJob(params: { jobId: string; correlationId: string }): Promise<SirConvertTranscriptJob> {
  return await createBrowserSirConvertTranscriptGatewayClient().getTranscriptJob(params);
}

export async function getTranscriptResult(params: { jobId: string; correlationId: string }): Promise<SirConvertTranscriptTerminalResult> {
  return await createBrowserSirConvertTranscriptGatewayClient().getTranscriptResult(params);
}

export async function listTranscriptArtifacts(params: { jobId: string; correlationId: string }): Promise<SirConvertTranscriptArtifactManifest> {
  return await createBrowserSirConvertTranscriptGatewayClient().listTranscriptArtifacts(params);
}

export async function downloadTranscriptJson(params: { jobId: string; correlationId: string }): Promise<TranscriptJson> {
  return await createBrowserSirConvertTranscriptGatewayClient().downloadTranscriptJson(params);
}

export async function cancelTranscriptJob(params: { jobId: string; correlationId: string }): Promise<SirConvertTranscriptCancelResult> {
  return await createBrowserSirConvertTranscriptGatewayClient().cancelTranscriptJob(params);
}
