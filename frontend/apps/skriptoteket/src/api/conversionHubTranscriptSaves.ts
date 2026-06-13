/**
 * Conversion Hub transcript save API client.
 *
 * Domain purpose:
 *   Persist canonical transcript JSON from authenticated Sir Convert Gateway
 *   runs into Skriptoteket-owned Conversion Hub transcript records.
 *
 * Relationships:
 *   - Consumed by `ConversionHubTranscriptHost`.
 *   - Uses parsed `TranscriptJson` from `sirConvertGateway` while preserving
 *     raw canonical JSON when available.
 */

import { apiFetch, apiGet, apiPost } from "./client";
import type { TranscriptJson, TranscriptSpeakerControl } from "./sirConvertGateway";

type JsonRecord = Record<string, unknown>;

export type RegisterTranscriptConversionHubJobRequest = {
  upstream_job_id: string;
  input_filename: string;
  correlation_id: string | null;
  status: "succeeded";
};

export type RegisterTranscriptConversionHubJobResult = {
  job_id: string;
  upstream_job_id: string;
  status: "succeeded";
};

export type SaveConversionHubTranscriptRequest = {
  sir_convert_job_id: string;
  artifact_key: "transcript_json";
  source_filename: string;
  transcript_json: JsonRecord;
  transcript_schema_version: string;
  language_code: string | null;
  diarization_mode: TranscriptSpeakerControl["mode"];
  speaker_count: number | null;
  speaker_min: number | null;
  speaker_max: number | null;
  generated_at: string | null;
  correlation_id: string | null;
};

export type ConversionHubSavedTranscriptResponse = SaveConversionHubTranscriptRequest & {
  transcript_id: string;
  owner_user_id: string;
  conversion_hub_job_id: string;
  created_at: string;
  updated_at: string;
};

export type ConversionHubTranscriptSpeakerOverlayEntry = {
  canonical_speaker_label: string;
  display_name: string;
};

export type UpdateConversionHubTranscriptSpeakerOverlaysRequest = {
  overlays: ConversionHubTranscriptSpeakerOverlayEntry[];
};

export type ConversionHubTranscriptSpeakerOverlaysResponse = {
  transcript_id: string;
  overlays: ConversionHubTranscriptSpeakerOverlayEntry[];
  updated_at: string | null;
};

const TRANSCRIPT_SAVE_ROOT = "/api/v1/apps/documents.conversion_hub/transcripts";

function isRecord(value: unknown): value is JsonRecord {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function nestedRecord(root: JsonRecord | null | undefined, key: string): JsonRecord | null {
  const value = root?.[key];
  return isRecord(value) ? value : null;
}

function stringField(root: JsonRecord | null | undefined, key: string): string | null {
  const value = root?.[key];
  return typeof value === "string" && value.length > 0 ? value : null;
}

function languageCode(rawJson: JsonRecord): string | null {
  const language = nestedRecord(rawJson, "language");
  return stringField(language, "detected") ?? stringField(language, "requested");
}

function generatedAt(rawJson: JsonRecord): string | null {
  const runtime = nestedRecord(rawJson, "runtime");
  const metadataRuntime = nestedRecord(nestedRecord(rawJson, "metadata"), "runtime");
  return stringField(runtime, "generated_at") ?? stringField(metadataRuntime, "generated_at");
}

function normalizedTranscriptJson(transcript: TranscriptJson): JsonRecord {
  return {
    schema_version: transcript.schemaVersion,
    transcript: {
      text: transcript.transcriptText,
      segments: transcript.segments.map((segment) => ({
        id: segment.id,
        start_seconds: segment.startSeconds,
        end_seconds: segment.endSeconds,
        speaker_label: segment.speakerLabel,
        text: segment.text,
      })),
    },
  };
}

export function buildSaveTranscriptRequest(params: {
  correlationId: string | null;
  sirConvertJobId: string;
  sourceFilename: string;
  speakerControl: TranscriptSpeakerControl;
  transcript: TranscriptJson;
}): SaveConversionHubTranscriptRequest {
  const rawJson = params.transcript.rawJson ?? normalizedTranscriptJson(params.transcript);
  return {
    sir_convert_job_id: params.sirConvertJobId,
    artifact_key: "transcript_json",
    source_filename: params.sourceFilename,
    transcript_json: rawJson,
    transcript_schema_version: params.transcript.schemaVersion,
    language_code: languageCode(rawJson),
    diarization_mode: params.speakerControl.mode,
    speaker_count:
      params.speakerControl.mode === "known_speaker_count"
        ? params.speakerControl.speakerCount
        : null,
    speaker_min:
      params.speakerControl.mode === "speaker_range" ? params.speakerControl.minSpeakers : null,
    speaker_max:
      params.speakerControl.mode === "speaker_range" ? params.speakerControl.maxSpeakers : null,
    generated_at: generatedAt(rawJson),
    correlation_id: params.correlationId,
  };
}

export async function registerTranscriptConversionHubJob(params: {
  request: RegisterTranscriptConversionHubJobRequest;
}): Promise<RegisterTranscriptConversionHubJobResult> {
  return await apiPost<RegisterTranscriptConversionHubJobResult>(
    `${TRANSCRIPT_SAVE_ROOT}/jobs`,
    params.request,
  );
}

export async function saveConversionHubTranscript(params: {
  conversionHubJobId: string;
  request: SaveConversionHubTranscriptRequest;
}): Promise<ConversionHubSavedTranscriptResponse> {
  return await apiPost<ConversionHubSavedTranscriptResponse>(
    `${TRANSCRIPT_SAVE_ROOT}/jobs/${encodeURIComponent(params.conversionHubJobId)}`,
    params.request,
  );
}

export async function getConversionHubTranscript(params: {
  transcriptId: string;
}): Promise<ConversionHubSavedTranscriptResponse> {
  return await apiGet<ConversionHubSavedTranscriptResponse>(
    `${TRANSCRIPT_SAVE_ROOT}/${encodeURIComponent(params.transcriptId)}`,
  );
}

export async function getConversionHubTranscriptSpeakerOverlays(params: {
  transcriptId: string;
}): Promise<ConversionHubTranscriptSpeakerOverlaysResponse> {
  return await apiGet<ConversionHubTranscriptSpeakerOverlaysResponse>(
    `${TRANSCRIPT_SAVE_ROOT}/${encodeURIComponent(params.transcriptId)}/speaker-overlays`,
  );
}

export async function updateConversionHubTranscriptSpeakerOverlays(params: {
  transcriptId: string;
  request: UpdateConversionHubTranscriptSpeakerOverlaysRequest;
}): Promise<ConversionHubTranscriptSpeakerOverlaysResponse> {
  return await apiFetch<ConversionHubTranscriptSpeakerOverlaysResponse>(
    `${TRANSCRIPT_SAVE_ROOT}/${encodeURIComponent(params.transcriptId)}/speaker-overlays`,
    { method: "PUT", body: params.request },
  );
}
