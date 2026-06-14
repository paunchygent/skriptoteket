/**
 * Conversion Hub transcript formatter export API client.
 *
 * Domain purpose:
 *   Record saved-transcript formatter export intent and read product-owned
 *   export state after Skriptoteket has created overlay-aware files.
 *
 * Relationships:
 *   - Consumed by `ConversionHubTranscriptHost`.
 *   - Keeps Sir Convert replay submission and artifact verification on the
 *     backend side of the Conversion Hub boundary.
 */

import { apiGet, apiPost } from "./client";

export const DEFAULT_TRANSCRIPT_FORMATTER_EXPORT_ARTIFACTS = [
  "txt",
  "md",
  "vtt",
  "srt",
] as const;

export type ConversionHubTranscriptFormatterOutputArtifact =
  (typeof DEFAULT_TRANSCRIPT_FORMATTER_EXPORT_ARTIFACTS)[number];

export type ConversionHubTranscriptFormatterExportStatus =
  | "not_requested"
  | "pending"
  | "running"
  | "succeeded"
  | "failed";

export type ConversionHubTranscriptFormatterArtifactKey =
  | "transcript_txt"
  | "transcript_md"
  | "transcript_vtt"
  | "transcript_srt";

export type ConversionHubTranscriptFormatterArtifactRef = {
  requested_artifact: ConversionHubTranscriptFormatterOutputArtifact;
  artifact_key: ConversionHubTranscriptFormatterArtifactKey;
  filename: string;
  content_type: string;
  size_bytes: number;
};

export type ConversionHubTranscriptFormatterExportRequest = {
  requested_artifacts: ConversionHubTranscriptFormatterOutputArtifact[];
};

export type ConversionHubTranscriptFormatterExportResponse = {
  transcript_id: string;
  conversion_hub_job_id: string | null;
  status: ConversionHubTranscriptFormatterExportStatus;
  requested_artifacts: ConversionHubTranscriptFormatterOutputArtifact[];
  artifacts: ConversionHubTranscriptFormatterArtifactRef[];
  error_message: string | null;
  created_at: string | null;
  updated_at: string | null;
};

const TRANSCRIPT_EXPORT_ROOT = "/api/v1/apps/documents.conversion_hub/transcripts";

function formatterExportUrl(transcriptId: string): string {
  return `${TRANSCRIPT_EXPORT_ROOT}/${encodeURIComponent(transcriptId)}/formatter-exports`;
}

function requestedArtifacts(
  artifacts?: ConversionHubTranscriptFormatterOutputArtifact[],
): ConversionHubTranscriptFormatterOutputArtifact[] {
  return [...(artifacts ?? DEFAULT_TRANSCRIPT_FORMATTER_EXPORT_ARTIFACTS)];
}

export async function requestConversionHubTranscriptFormatterExport(params: {
  transcriptId: string;
  requestedArtifacts?: ConversionHubTranscriptFormatterOutputArtifact[];
}): Promise<ConversionHubTranscriptFormatterExportResponse> {
  const request: ConversionHubTranscriptFormatterExportRequest = {
    requested_artifacts: requestedArtifacts(params.requestedArtifacts),
  };
  return await apiPost<ConversionHubTranscriptFormatterExportResponse>(
    formatterExportUrl(params.transcriptId),
    request,
  );
}

export async function getConversionHubTranscriptFormatterExport(params: {
  transcriptId: string;
}): Promise<ConversionHubTranscriptFormatterExportResponse> {
  return await apiGet<ConversionHubTranscriptFormatterExportResponse>(
    formatterExportUrl(params.transcriptId),
  );
}
