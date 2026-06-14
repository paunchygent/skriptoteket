/**
 * Conversion Hub transcript formatter artifact action API client.
 *
 * Domain purpose:
 *   Download and save product-owned transcript formatter artifacts through
 *   Skriptoteket-owned authorization and Mina filer persistence routes.
 *
 * Relationships:
 *   - Consumed by `ConversionHubTranscriptHost` artifact action controls.
 *   - Uses protected API helpers from `client.ts`; never calls Sir Convert
 *     artifact URLs directly from the browser.
 */

import { apiFetchBlobResponse, apiPost, type ApiBlobResponse } from "./client";
import type {
  ConversionHubTranscriptFormatterArtifactRef,
} from "./conversionHubTranscriptFormatterExports";

export type TranscriptFormatterArtifactKey =
  ConversionHubTranscriptFormatterArtifactRef["artifact_key"];

export type ConversionHubTranscriptFormatterSavedArtifact = {
  source_artifact_id: string;
  vault_artifact: {
    file_id: string;
    name: string;
    bytes: number;
    created_at: string;
  };
};

const TRANSCRIPT_ARTIFACT_ROOT = "/api/v1/apps/documents.conversion_hub/transcripts";

function formatterArtifactUrl(params: {
  transcriptId: string;
  artifactKey: TranscriptFormatterArtifactKey;
  action: "download" | "save";
}): string {
  return [
    TRANSCRIPT_ARTIFACT_ROOT,
    encodeURIComponent(params.transcriptId),
    "formatter-artifacts",
    encodeURIComponent(params.artifactKey),
    params.action,
  ].join("/");
}

export async function downloadConversionHubTranscriptFormatterArtifact(params: {
  transcriptId: string;
  artifactKey: TranscriptFormatterArtifactKey;
}): Promise<ApiBlobResponse> {
  return await apiFetchBlobResponse(
    formatterArtifactUrl({ ...params, action: "download" }),
    { method: "GET" },
  );
}

export async function saveConversionHubTranscriptFormatterArtifact(params: {
  transcriptId: string;
  artifactKey: TranscriptFormatterArtifactKey;
}): Promise<ConversionHubTranscriptFormatterSavedArtifact> {
  return await apiPost<ConversionHubTranscriptFormatterSavedArtifact>(
    formatterArtifactUrl({ ...params, action: "save" }),
  );
}
