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
  SirConvertTranscriptFormatterReplayArtifactManifest,
  SirConvertTranscriptFormatterReplaySubmittedJob,
  SirConvertTranscriptFormatterReplayTerminalResult,
  TranscriptFormatterReplaySubmitParams,
} from "./transcriptTypes";

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
  };
}
