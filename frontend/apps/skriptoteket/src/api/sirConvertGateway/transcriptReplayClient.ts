/**
 * Sir Convert transcript formatter replay Gateway client.
 *
 * Purpose:
 *   Submit saved transcript JSON plus overlay-aware replay JobSpecs through
 *   the authenticated HuleEdu Sir Convert Gateway and read producer artifact
 *   metadata without downloading formatter outputs locally.
 *
 * Relationships:
 *   - Composed into `client.ts` for the public Sir Convert Gateway client.
 *   - Uses `transcriptReplayParsers.ts` for fail-closed replay contracts.
 */

import { readJsonOrThrow } from "./parsers";
import {
  parseTranscriptFormatterReplayArtifactManifest,
  parseTranscriptFormatterReplayJob,
  parseTranscriptFormatterReplayResult,
} from "./transcriptReplayParsers";
import { stableJsonStringify } from "./requestContext";
import { toSirConvertGatewayUrl } from "./urls";
import {
  buildJsonHeaders,
  buildUnsafeHeaders,
  normalizeWaitSeconds,
  type CsrfTokenProvider,
} from "./headers";
import type {
  SirConvertTranscriptFormatterOutputArtifact,
  SirConvertTranscriptFormatterReplayArtifactBlob,
  SirConvertTranscriptFormatterReplayArtifactManifest,
  SirConvertTranscriptFormatterReplaySubmittedJob,
  SirConvertTranscriptFormatterReplayTerminalResult,
  TranscriptFormatterReplaySubmitParams,
} from "./transcriptTypes";

const ARTIFACT_RECEIPT_VERSION_HEADER = "X-HuleEdu-Sir-Convert-Artifact-Receipt-Version";
const ARTIFACT_RECEIPT_PAYLOAD_HEADER = "X-HuleEdu-Sir-Convert-Artifact-Receipt";
const ARTIFACT_RECEIPT_KEY_ID_HEADER = "X-HuleEdu-Sir-Convert-Artifact-Receipt-Key-Id";
const ARTIFACT_RECEIPT_SIGNATURE_HEADER = "X-HuleEdu-Sir-Convert-Artifact-Receipt-Signature";

export type TranscriptFormatterReplayGatewayClientDependencies = {
  fetcher: typeof fetch;
  ensureCsrfToken: CsrfTokenProvider;
};

export type TranscriptFormatterReplayGatewayClient = {
  submitTranscriptFormatterReplay(
    params: TranscriptFormatterReplaySubmitParams,
  ): Promise<SirConvertTranscriptFormatterReplaySubmittedJob>;
  getTranscriptFormatterReplayResult(params: {
    jobId: string;
    correlationId: string;
  }): Promise<SirConvertTranscriptFormatterReplayTerminalResult>;
  listTranscriptFormatterReplayArtifacts(params: {
    jobId: string;
    correlationId: string;
    requestedArtifacts: readonly SirConvertTranscriptFormatterOutputArtifact[];
  }): Promise<SirConvertTranscriptFormatterReplayArtifactManifest>;
  downloadTranscriptFormatterReplayArtifact(params: {
    artifactKey: SirConvertTranscriptFormatterReplayArtifactBlob["artifactKey"];
    jobId: string;
    correlationId: string;
  }): Promise<SirConvertTranscriptFormatterReplayArtifactBlob>;
};

export function createTranscriptFormatterReplayGatewayClient(
  dependencies: TranscriptFormatterReplayGatewayClientDependencies,
): TranscriptFormatterReplayGatewayClient {
  return {
    async submitTranscriptFormatterReplay(params) {
      const formData = new FormData();
      const transcriptFile = new File([stableJsonStringify(params.transcriptJson)], params.gatewayFilename, {
        type: params.contentType,
      });
      formData.append("file", transcriptFile, transcriptFile.name);
      formData.append("job_spec", stableJsonStringify(params.jobSpec));

      const response = await dependencies.fetcher(
        toSirConvertGatewayUrl(`/jobs?wait_seconds=${normalizeWaitSeconds(params.waitSeconds)}`),
        {
          method: "POST",
          headers: await buildUnsafeHeaders({
            correlationId: params.correlationId,
            idempotencyKey: params.idempotencyKey,
            ensureCsrfToken: dependencies.ensureCsrfToken,
          }),
          body: formData,
          credentials: "include",
        },
      );
      const submitted = await readJsonOrThrow(response, parseTranscriptFormatterReplayJob);
      return {
        ...submitted,
        idempotentReplay: response.headers.get("X-Idempotent-Replay")?.toLowerCase() === "true",
        requestContext: {
          correlationId: params.correlationId,
          idempotencyKey: params.idempotencyKey,
          jobSpec: params.jobSpec,
          requestedArtifacts: params.requestedArtifacts,
        },
      };
    },

    async getTranscriptFormatterReplayResult(params) {
      const response = await dependencies.fetcher(
        toSirConvertGatewayUrl(`/jobs/${params.jobId}/result`),
        {
          method: "GET",
          headers: buildJsonHeaders(params.correlationId),
          credentials: "include",
        },
      );
      return await readJsonOrThrow(response, parseTranscriptFormatterReplayResult);
    },

    async listTranscriptFormatterReplayArtifacts(params) {
      const response = await dependencies.fetcher(
        toSirConvertGatewayUrl(`/jobs/${params.jobId}/artifacts`),
        {
          method: "GET",
          headers: buildJsonHeaders(params.correlationId),
          credentials: "include",
        },
      );
      return await readJsonOrThrow(response, (payload) =>
        parseTranscriptFormatterReplayArtifactManifest(payload, params.requestedArtifacts),
      );
    },

    async downloadTranscriptFormatterReplayArtifact(params) {
      const response = await dependencies.fetcher(
        toSirConvertGatewayUrl(`/jobs/${params.jobId}/artifacts/${params.artifactKey}`),
        {
          method: "GET",
          headers: buildJsonHeaders(params.correlationId),
          credentials: "include",
        },
      );
      if (!response.ok) {
        await readJsonOrThrow(response, () => ({}));
      }
      const receiptVersion = response.headers.get(ARTIFACT_RECEIPT_VERSION_HEADER);
      const receiptPayload = response.headers.get(ARTIFACT_RECEIPT_PAYLOAD_HEADER);
      const receiptKeyId = response.headers.get(ARTIFACT_RECEIPT_KEY_ID_HEADER);
      const receiptSignature = response.headers.get(ARTIFACT_RECEIPT_SIGNATURE_HEADER);
      if (
        receiptVersion !== "1"
        || !receiptPayload
        || !receiptKeyId
        || !receiptSignature
      ) {
        throw new Error("Gateway artifact receipt is missing.");
      }
      return {
        artifactKey: params.artifactKey,
        contentType: response.headers.get("content-type") ?? "application/octet-stream",
        bytes: await response.arrayBuffer(),
        receipt: {
          receipt_version: 1,
          payload: receiptPayload,
          key_id: receiptKeyId,
          signature: receiptSignature,
        },
      };
    },
  };
}
