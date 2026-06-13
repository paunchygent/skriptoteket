/**
 * Conversion Hub transcript formatter replay API client.
 *
 * Domain purpose:
 *   Orchestrate saved-transcript formatter replay by asking Skriptoteket for
 *   owner-scoped transcript JSON and overlay JobSpecs, submitting through
 *   HuleEdu Gateway, then recording producer-owned artifact references.
 *
 * Relationships:
 *   - Consumed by `ConversionHubTranscriptHost`.
 *   - Delegates producer contract validation to `sirConvertGateway`.
 */

import { apiPost } from "./client";
import {
  createBrowserSirConvertGatewayClient,
  SIR_CONVERT_TRANSCRIPT_ARTIFACT_KEY_BY_OUTPUT_ARTIFACT,
  type SirConvertTranscriptFormatterOutputArtifact,
  type SirConvertTranscriptFormatterReplayArtifactBlob,
  type SirConvertTranscriptFormatterReplayJobSpec,
  type SirConvertTranscriptFormatterReplayTerminalResult,
  type SirConvertTranscriptJob,
  type TranscriptFormatterReplaySubmitParams,
} from "./sirConvertGateway";

type JsonRecord = Record<string, unknown>;

export type ConversionHubTranscriptFormatterArtifactRef = {
  requested_artifact: SirConvertTranscriptFormatterOutputArtifact;
  artifact_key: "transcript_txt" | "transcript_md" | "transcript_vtt" | "transcript_srt";
  filename: string;
  content_type: string;
  size_bytes: number;
  sha256: string;
  retrieval_path: string;
};

export type ConversionHubTranscriptFormatterReplayPrepareRequest = {
  requested_artifacts: SirConvertTranscriptFormatterOutputArtifact[];
};

export type ConversionHubTranscriptFormatterReplayPrepareResponse = {
  transcript_id: string;
  correlation_id: string;
  idempotency_key: string;
  gateway_filename: string;
  content_type: "application/json";
  transcript_json: JsonRecord;
  job_spec: SirConvertTranscriptFormatterReplayJobSpec;
};

export type ConversionHubTranscriptFormatterReplayCompleteRequest = {
  sir_convert_job_id: string;
  correlation_id: string | null;
  status: "succeeded";
  requested_artifacts: SirConvertTranscriptFormatterOutputArtifact[];
  result: JsonRecord;
  artifact_payloads: {
    artifact_key: ConversionHubTranscriptFormatterArtifactRef["artifact_key"];
    content_type: string;
    content_base64: string;
    receipt: SirConvertTranscriptFormatterReplayArtifactBlob["receipt"];
  }[];
};

export type ConversionHubTranscriptFormatterReplayResponse = {
  transcript_id: string;
  conversion_hub_job_id: string;
  sir_convert_job_id: string;
  correlation_id: string | null;
  status: "succeeded";
  requested_artifacts: SirConvertTranscriptFormatterOutputArtifact[];
  artifacts: ConversionHubTranscriptFormatterArtifactRef[];
};

export type TranscriptFormatterReplayCommandGatewayClient = {
  submitTranscriptFormatterReplay(
    params: TranscriptFormatterReplaySubmitParams,
  ): Promise<{ jobId: string; status: SirConvertTranscriptJob["status"] }>;
  getTranscriptJob(params: {
    jobId: string;
    correlationId: string;
  }): Promise<SirConvertTranscriptJob>;
  getTranscriptFormatterReplayResult(params: {
    jobId: string;
    correlationId: string;
  }): Promise<SirConvertTranscriptFormatterReplayTerminalResult>;
  listTranscriptFormatterReplayArtifacts(params: {
    jobId: string;
    correlationId: string;
    requestedArtifacts: readonly SirConvertTranscriptFormatterOutputArtifact[];
  }): Promise<unknown>;
  downloadTranscriptFormatterReplayArtifact(params: {
    artifactKey: ConversionHubTranscriptFormatterArtifactRef["artifact_key"];
    jobId: string;
    correlationId: string;
  }): Promise<SirConvertTranscriptFormatterReplayArtifactBlob>;
};

const TRANSCRIPT_REPLAY_ROOT = "/api/v1/apps/documents.conversion_hub/transcripts";
const DEFAULT_REPLAY_ARTIFACTS: SirConvertTranscriptFormatterOutputArtifact[] = [
  "txt",
  "md",
  "vtt",
  "srt",
];
const ACTIVE_REPLAY_STATUSES = new Set<SirConvertTranscriptJob["status"]>([
  "submitted",
  "queued",
  "running",
  "processing",
]);

function replayUrl(transcriptId: string, suffix: "prepare" | "complete"): string {
  return `${TRANSCRIPT_REPLAY_ROOT}/${encodeURIComponent(transcriptId)}/formatter-replay/${suffix}`;
}

function waitForReplayPoll(milliseconds: number): Promise<void> {
  if (milliseconds <= 0) return Promise.resolve();
  return new Promise((resolve) => {
    globalThis.setTimeout(resolve, milliseconds);
  });
}

async function waitForTerminalReplayJob(params: {
  gatewayClient: TranscriptFormatterReplayCommandGatewayClient;
  correlationId: string;
  jobId: string;
  initialStatus: SirConvertTranscriptJob["status"];
  pollIntervalMs: number;
}): Promise<SirConvertTranscriptJob["status"]> {
  let status = params.initialStatus;
  while (ACTIVE_REPLAY_STATUSES.has(status)) {
    await waitForReplayPoll(params.pollIntervalMs);
    const job = await params.gatewayClient.getTranscriptJob({
      correlationId: params.correlationId,
      jobId: params.jobId,
    });
    status = job.status;
  }
  return status;
}

function artifactKeyForRequestedArtifact(
  artifact: SirConvertTranscriptFormatterOutputArtifact,
): ConversionHubTranscriptFormatterArtifactRef["artifact_key"] {
  return SIR_CONVERT_TRANSCRIPT_ARTIFACT_KEY_BY_OUTPUT_ARTIFACT[artifact];
}

function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  const chunkSize = 0x8000;
  let binary = "";
  for (let offset = 0; offset < bytes.length; offset += chunkSize) {
    binary += String.fromCharCode(...bytes.subarray(offset, offset + chunkSize));
  }
  return globalThis.btoa(binary);
}

async function downloadReplayArtifactPayloads(params: {
  gatewayClient: TranscriptFormatterReplayCommandGatewayClient;
  correlationId: string;
  jobId: string;
  requestedArtifacts: readonly SirConvertTranscriptFormatterOutputArtifact[];
}): Promise<ConversionHubTranscriptFormatterReplayCompleteRequest["artifact_payloads"]> {
  const payloads = await Promise.all(
    params.requestedArtifacts.map(async (requestedArtifact) => {
      const artifactKey = artifactKeyForRequestedArtifact(requestedArtifact);
      const artifact = await params.gatewayClient.downloadTranscriptFormatterReplayArtifact({
        artifactKey,
        correlationId: params.correlationId,
        jobId: params.jobId,
      });
      return {
        artifact_key: artifact.artifactKey,
        content_type: artifact.contentType,
        content_base64: arrayBufferToBase64(artifact.bytes),
        receipt: artifact.receipt,
      };
    }),
  );
  return payloads;
}

export async function prepareConversionHubTranscriptFormatterReplay(params: {
  transcriptId: string;
  request: ConversionHubTranscriptFormatterReplayPrepareRequest;
}): Promise<ConversionHubTranscriptFormatterReplayPrepareResponse> {
  return await apiPost<ConversionHubTranscriptFormatterReplayPrepareResponse>(
    replayUrl(params.transcriptId, "prepare"),
    params.request,
  );
}

export async function completeConversionHubTranscriptFormatterReplay(params: {
  transcriptId: string;
  request: ConversionHubTranscriptFormatterReplayCompleteRequest;
}): Promise<ConversionHubTranscriptFormatterReplayResponse> {
  return await apiPost<ConversionHubTranscriptFormatterReplayResponse>(
    replayUrl(params.transcriptId, "complete"),
    params.request,
  );
}

export async function requestConversionHubTranscriptFormatterReplay(params: {
  transcriptId: string;
  requestedArtifacts?: SirConvertTranscriptFormatterOutputArtifact[];
  gatewayClient?: TranscriptFormatterReplayCommandGatewayClient;
  pollIntervalMs?: number;
}): Promise<ConversionHubTranscriptFormatterReplayResponse> {
  const requestedArtifacts = params.requestedArtifacts ?? DEFAULT_REPLAY_ARTIFACTS;
  const prepared = await prepareConversionHubTranscriptFormatterReplay({
    transcriptId: params.transcriptId,
    request: { requested_artifacts: requestedArtifacts },
  });
  const gatewayClient = params.gatewayClient ?? createBrowserSirConvertGatewayClient();
  const submitted = await gatewayClient.submitTranscriptFormatterReplay({
    contentType: prepared.content_type,
    correlationId: prepared.correlation_id,
    gatewayFilename: prepared.gateway_filename,
    idempotencyKey: prepared.idempotency_key,
    jobSpec: prepared.job_spec,
    requestedArtifacts,
    transcriptJson: prepared.transcript_json,
    waitSeconds: 20,
  });
  const terminalStatus = await waitForTerminalReplayJob({
    gatewayClient,
    correlationId: prepared.correlation_id,
    jobId: submitted.jobId,
    initialStatus: submitted.status,
    pollIntervalMs: params.pollIntervalMs ?? 2000,
  });
  if (terminalStatus !== "succeeded") {
    throw new Error("Sir Convert replay job did not succeed.");
  }
  const result = await gatewayClient.getTranscriptFormatterReplayResult({
    correlationId: prepared.correlation_id,
    jobId: submitted.jobId,
  });
  const artifactPayloads = await downloadReplayArtifactPayloads({
    correlationId: prepared.correlation_id,
    gatewayClient,
    jobId: submitted.jobId,
    requestedArtifacts,
  });
  return await completeConversionHubTranscriptFormatterReplay({
    transcriptId: params.transcriptId,
    request: {
      sir_convert_job_id: submitted.jobId,
      correlation_id: prepared.correlation_id,
      status: "succeeded",
      requested_artifacts: requestedArtifacts,
      result: result.rawResult,
      artifact_payloads: artifactPayloads,
    },
  });
}
