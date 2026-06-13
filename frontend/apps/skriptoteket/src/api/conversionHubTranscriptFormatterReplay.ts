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
  type SirConvertTranscriptFormatterOutputArtifact,
  type SirConvertTranscriptFormatterReplayArtifactManifest,
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
  artifact_manifest: JsonRecord;
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
  }): Promise<SirConvertTranscriptFormatterReplayArtifactManifest>;
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
  const manifest = await gatewayClient.listTranscriptFormatterReplayArtifacts({
    correlationId: prepared.correlation_id,
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
      artifact_manifest: manifest.rawManifest,
    },
  });
}
