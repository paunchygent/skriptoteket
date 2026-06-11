/**
 * Sir Convert transcript response parsers.
 *
 * Purpose:
 *   Validate transcript lifecycle, artifact manifests, and canonical
 *   `transcript_json` payloads before teacher-facing UI treats them as success.
 *
 * Relationships:
 *   - `client.ts` delegates transcript response decoding here.
 *   - `transcriptTypes.ts` defines the parsed consumer contracts.
 */

import {
  SIR_CONVERT_ARTIFACT_AVAILABILITIES,
  SIR_CONVERT_ARTIFACT_FAILED,
  SIR_CONVERT_ARTIFACT_UNAVAILABLE,
} from "./contractValues";
import type { SirConvertArtifactAvailability, SirConvertJobStatus } from "./types";
import type {
  SirConvertTranscriptArtifactEntry,
  SirConvertTranscriptArtifactManifest,
  SirConvertTranscriptAudioProgress,
  SirConvertTranscriptJob,
  SirConvertTranscriptTerminalResult,
  TranscriptJson,
  TranscriptSegment,
} from "./transcriptTypes";

type JsonRecord = Record<string, unknown>;

function isRecord(value: unknown): value is JsonRecord {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function readRecord(value: unknown, fieldName: string): JsonRecord {
  if (isRecord(value)) return value;
  throw new Error(`Sir Convert transcript field '${fieldName}' is not an object.`);
}

function readString(value: unknown, fieldName: string): string {
  if (typeof value === "string" && value.length > 0) return value;
  throw new Error(`Sir Convert transcript field '${fieldName}' is missing.`);
}

function readNullableString(value: unknown, fieldName: string): string | null {
  if (value === null || value === undefined) return null;
  if (typeof value === "string") return value;
  throw new Error(`Sir Convert transcript field '${fieldName}' is not a string.`);
}

function readNumber(value: unknown, fieldName: string): number {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  throw new Error(`Sir Convert transcript field '${fieldName}' is not a number.`);
}

function readNullableNumber(value: unknown, fieldName: string): number | null {
  if (value === null || value === undefined) return null;
  return readNumber(value, fieldName);
}

function readStatus(value: unknown): SirConvertJobStatus {
  const status = readString(value, "status");
  if (
    status === "submitted" ||
    status === "queued" ||
    status === "running" ||
    status === "processing" ||
    status === "succeeded" ||
    status === "failed" ||
    status === "canceled" ||
    status === "cancelled"
  ) {
    return status;
  }
  throw new Error(`Unknown Sir Convert transcript status '${status}'.`);
}

function readAvailability(value: unknown): SirConvertArtifactAvailability {
  const availability = readString(value, "availability");
  if (SIR_CONVERT_ARTIFACT_AVAILABILITIES.includes(availability as SirConvertArtifactAvailability)) {
    return availability as SirConvertArtifactAvailability;
  }
  throw new Error(`Unknown Sir Convert transcript artifact availability '${availability}'.`);
}

function progressRecord(job: JsonRecord): JsonRecord {
  return isRecord(job.progress) ? job.progress : job;
}

function parseAudioProgress(job: JsonRecord): SirConvertTranscriptAudioProgress {
  const progress = progressRecord(job);
  return {
    totalMediaSeconds: readNullableNumber(
      progress.audio_total_media_seconds,
      "audio_total_media_seconds",
    ),
    processedMediaSeconds: readNullableNumber(
      progress.audio_processed_media_seconds,
      "audio_processed_media_seconds",
    ),
    percentComplete: readNullableNumber(progress.audio_percent_complete, "audio_percent_complete"),
    currentChunkIndex: readNullableNumber(
      progress.audio_current_chunk_index,
      "audio_current_chunk_index",
    ),
    totalChunks: readNullableNumber(progress.audio_total_chunks, "audio_total_chunks"),
  };
}

export function parseTranscriptJob(payload: unknown): SirConvertTranscriptJob {
  const root = readRecord(payload, "payload");
  const job = isRecord(root.job)
    ? root.job
    : {
        job_id: root.job_id,
        status: root.status,
        progress: root.progress,
        stage: root.stage,
      };
  const progress = progressRecord(job);
  return {
    jobId: readString(job.job_id, "job.job_id"),
    status: readStatus(job.status),
    stage: readNullableString(progress.stage ?? job.stage, "stage"),
    audioProgress: parseAudioProgress(job),
  };
}

function parseTranscriptResultJob(payload: unknown, root: JsonRecord): SirConvertTranscriptJob {
  if (isRecord(root.job) || typeof root.status === "string") {
    return parseTranscriptJob(payload);
  }
  return {
    jobId: readString(root.job_id, "job_id"),
    status: "succeeded",
    stage: null,
    audioProgress: {
      totalMediaSeconds: null,
      processedMediaSeconds: null,
      percentComplete: null,
      currentChunkIndex: null,
      totalChunks: null,
    },
  };
}

function readTranscriptPipeline(value: unknown): "audio_to_transcript_bundle_v2" {
  const pipelineUsed = readString(value, "conversion_metadata.pipeline_used");
  if (pipelineUsed === "audio_to_transcript_bundle_v2") {
    return pipelineUsed;
  }
  throw new Error(`Unknown Sir Convert transcript pipeline '${pipelineUsed}'.`);
}

function parseArtifactEntry(payload: unknown): SirConvertTranscriptArtifactEntry {
  const entry = readRecord(payload, "artifact");
  const artifactKey = readString(entry.artifact_key, "artifact_key");
  const availability = readAvailability(entry.availability);
  const unavailableCode =
    typeof entry.unavailable_code === "string" && entry.unavailable_code.length > 0
      ? entry.unavailable_code
      : undefined;
  if (
    (availability === SIR_CONVERT_ARTIFACT_UNAVAILABLE ||
      availability === SIR_CONVERT_ARTIFACT_FAILED) &&
    !unavailableCode
  ) {
    throw new Error(`Transcript artifact '${artifactKey}' requires unavailable_code.`);
  }
  const downloadPath =
    typeof entry.download_path === "string" && entry.download_path.length > 0
      ? entry.download_path
      : undefined;
  return {
    artifact_key: artifactKey,
    filename: readString(entry.filename, "filename"),
    content_type: readString(entry.content_type, "content_type"),
    availability,
    size_bytes: readNullableNumber(entry.size_bytes, "size_bytes"),
    sha256: readNullableString(entry.sha256, "sha256"),
    ...(downloadPath ? { download_path: downloadPath } : {}),
    ...(unavailableCode ? { unavailable_code: unavailableCode } : {}),
  };
}

export function parseTranscriptResult(payload: unknown): SirConvertTranscriptTerminalResult {
  const root = readRecord(payload, "payload");
  const result = readRecord(root.result, "result");
  const artifact = readRecord(result.artifact, "result.artifact");
  const metadata = readRecord(result.conversion_metadata, "result.conversion_metadata");
  return {
    job: parseTranscriptResultJob(payload, root),
    artifact: {
      filename: readString(artifact.filename, "result.artifact.filename"),
      content_type: readString(artifact.content_type, "result.artifact.content_type"),
      sha256: readNullableString(artifact.sha256, "result.artifact.sha256"),
      size_bytes: readNullableNumber(artifact.size_bytes, "result.artifact.size_bytes"),
    },
    conversion_metadata: {
      pipeline_used: readTranscriptPipeline(metadata.pipeline_used),
      backend_used: readString(metadata.backend_used, "conversion_metadata.backend_used"),
      acceleration_used: readString(
        metadata.acceleration_used,
        "conversion_metadata.acceleration_used",
      ),
      options_fingerprint: readString(
        metadata.options_fingerprint,
        "conversion_metadata.options_fingerprint",
      ),
    },
  };
}

export function parseTranscriptArtifactManifest(
  payload: unknown,
): SirConvertTranscriptArtifactManifest {
  const root = readRecord(payload, "manifest");
  const source = readRecord(root.source, "source");
  const format = readString(source.format, "source.format");
  if (format !== "audio") {
    throw new Error(`Unknown Sir Convert transcript source format '${format}'.`);
  }
  if (!Array.isArray(root.artifacts)) {
    throw new Error("Sir Convert transcript manifest is missing artifacts.");
  }
  const artifacts = root.artifacts.map((entry) => parseArtifactEntry(entry));
  return {
    schema_version: readString(root.schema_version, "schema_version"),
    job_id: readString(root.job_id, "job_id"),
    source: {
      filename: readString(source.filename, "source.filename"),
      sha256: readString(source.sha256, "source.sha256"),
      format: "audio",
    },
    bundle_status: readString(root.bundle_status, "bundle_status"),
    artifacts,
    transcriptJsonArtifact:
      artifacts.find((entry) => entry.artifact_key === "transcript_json") ?? null,
  };
}

function readOptionalStatus(record: JsonRecord, fieldName: string): string | null {
  const field = record[fieldName];
  if (isRecord(field)) {
    return readNullableString(field.status, `${fieldName}.status`);
  }
  if (typeof field === "string") {
    return field;
  }
  return null;
}

function assertSuccessfulTranscriptState(root: JsonRecord): void {
  const diarizationStatus = readOptionalStatus(root, "diarization");
  const diarization = isRecord(root.diarization) ? root.diarization : {};
  const modeUsed = readNullableString(diarization.mode_used, "diarization.mode_used");
  if (
    diarizationStatus === "failed" ||
    diarizationStatus === "unavailable" ||
    modeUsed === "diarization_unavailable"
  ) {
    throw new Error("Transcript JSON reports failed or unavailable diarization.");
  }
  const alignmentStatus =
    readOptionalStatus(root, "alignment") ?? readOptionalStatus(root, "segment_alignment");
  if (alignmentStatus === "failed") {
    throw new Error("Transcript JSON reports failed alignment.");
  }
}

function transcriptRecord(root: JsonRecord): JsonRecord {
  return isRecord(root.transcript) ? root.transcript : root;
}

function parseSegment(payload: unknown, index: number): TranscriptSegment {
  const segment = readRecord(payload, `segments[${index}]`);
  const speakerLabel = readNullableString(
    segment.speaker_label ?? segment.speaker,
    `segments[${index}].speaker_label`,
  );
  if (!speakerLabel) {
    throw new Error("Transcript segment is missing a speaker label.");
  }
  return {
    id: readString(segment.id ?? `segment_${index + 1}`, `segments[${index}].id`),
    startSeconds: readNumber(segment.start_seconds, `segments[${index}].start_seconds`),
    endSeconds: readNumber(segment.end_seconds, `segments[${index}].end_seconds`),
    speakerLabel,
    text: readString(segment.text, `segments[${index}].text`),
  };
}

export function parseTranscriptJson(payload: unknown): TranscriptJson {
  const root = readRecord(payload, "transcript_json");
  assertSuccessfulTranscriptState(root);
  const transcript = transcriptRecord(root);
  const rawSegments = transcript.segments;
  if (!Array.isArray(rawSegments) || rawSegments.length === 0) {
    throw new Error("Transcript JSON is missing non-empty segments.");
  }
  const transcriptText = readString(
    transcript.text ?? root.transcript_text ?? root.text,
    "transcript.text",
  );
  const segments = rawSegments.map((entry, index) => parseSegment(entry, index));
  return {
    schemaVersion: readString(root.schema_version, "schema_version"),
    transcriptText,
    segments,
  };
}
