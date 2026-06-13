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

import type { SirConvertJobStatus } from "./types";
import type {
  SirConvertTranscriptArtifactAvailability,
  SirConvertTranscriptArtifactEntry,
  SirConvertTranscriptArtifactKey,
  SirConvertTranscriptArtifactManifest,
  SirConvertTranscriptFormatterArtifactKey,
  SirConvertTranscriptJob,
  SirConvertTranscriptPhaseTimingKey,
  SirConvertTranscriptProgressPhase,
  SirConvertTranscriptProgressSnapshot,
  SirConvertTranscriptTerminalResult,
  TranscriptJson,
  TranscriptSegment,
} from "./transcriptTypes";
import {
  SIR_CONVERT_TRANSCRIPT_ARTIFACT_CONTENT_TYPES,
} from "./transcriptTypes";

type JsonRecord = Record<string, unknown>;

function isRecord(value: unknown): value is JsonRecord {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function hasOwnField(record: JsonRecord, fieldName: string): boolean {
  return Object.prototype.hasOwnProperty.call(record, fieldName);
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

function readNullableNonNegativeNumber(value: unknown, fieldName: string): number | null {
  const numberValue = readNullableNumber(value, fieldName);
  if (numberValue === null || numberValue >= 0) return numberValue;
  throw new Error(`Sir Convert transcript field '${fieldName}' is negative.`);
}

function readNullablePercent(value: unknown, fieldName: string): number | null {
  const numberValue = readNullableNonNegativeNumber(value, fieldName);
  if (numberValue === null || numberValue <= 100) return numberValue;
  throw new Error(`Sir Convert transcript field '${fieldName}' is outside 0..100.`);
}

function readNullableNonNegativeInteger(value: unknown, fieldName: string): number | null {
  const numberValue = readNullableNonNegativeNumber(value, fieldName);
  if (numberValue === null || Number.isInteger(numberValue)) return numberValue;
  throw new Error(`Sir Convert transcript field '${fieldName}' is not an integer.`);
}

function readNullableDateTime(value: unknown, fieldName: string): string | null {
  const stringValue = readNullableString(value, fieldName);
  if (stringValue === null) return null;
  if (stringValue.length > 0 && Number.isFinite(Date.parse(stringValue))) return stringValue;
  throw new Error(`Sir Convert transcript field '${fieldName}' is not a datetime.`);
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

function readArtifactKey(value: unknown): SirConvertTranscriptArtifactKey {
  const artifactKey = readString(value, "artifact_key");
  switch (artifactKey) {
    case "transcript_json":
    case "transcript_txt":
    case "transcript_md":
    case "transcript_vtt":
    case "transcript_srt":
      return artifactKey;
    default:
      throw new Error(`Unknown Sir Convert transcript artifact key '${artifactKey}'.`);
  }
}

function readAvailability(value: unknown): SirConvertTranscriptArtifactAvailability {
  const availability = readString(value, "availability");
  switch (availability) {
    case "available":
    case "unavailable":
    case "failed":
    case "unrequested":
      return availability;
    default:
      throw new Error(`Unknown Sir Convert transcript artifact availability '${availability}'.`);
  }
}

function readProgressPhase(value: unknown, fieldName: string): SirConvertTranscriptProgressPhase {
  const phase = readString(value, fieldName);
  switch (phase) {
    case "submitted":
    case "queued":
    case "starting":
    case "probing_media":
    case "normalizing_audio":
    case "transcribing":
    case "diarizing":
    case "aligning_segments":
    case "packaging":
    case "succeeded":
    case "failed":
    case "canceled":
    case "cancelled":
      return phase;
    default:
      throw new Error(`Unknown Sir Convert transcript progress phase '${phase}'.`);
  }
}

function readPhaseTimingKey(value: string): SirConvertTranscriptPhaseTimingKey {
  switch (value) {
    case "ocr_layout_extract_ms":
    case "markdown_normalize_ms":
    case "formula_enrichment_ms":
    case "checkpoint_persist_ms":
    case "final_artifact_persist_ms":
    case "chunk_total_ms":
    case "conversion_total_ms":
      return value;
    default:
      throw new Error(`Unknown Sir Convert transcript phase timing '${value}'.`);
  }
}

function parsePhaseTimings(
  value: unknown,
): Partial<Record<SirConvertTranscriptPhaseTimingKey, number>> {
  if (value === null || value === undefined) return {};
  const timings = readRecord(value, "phase_timings_ms");
  const parsed: Partial<Record<SirConvertTranscriptPhaseTimingKey, number>> = {};
  for (const [key, timingValue] of Object.entries(timings)) {
    parsed[readPhaseTimingKey(key)] = readNullableNonNegativeInteger(
      timingValue,
      `phase_timings_ms.${key}`,
    ) ?? 0;
  }
  return parsed;
}

function emptyProgress(status: SirConvertJobStatus): SirConvertTranscriptProgressSnapshot {
  return {
    status,
    phase: null,
    lastHeartbeatAt: null,
    currentPhaseStartedAt: null,
    processedMediaSeconds: null,
    totalMediaSeconds: null,
    percentComplete: null,
    currentChunkIndex: null,
    totalChunks: null,
    phaseTimingsMs: {},
  };
}

function progressRecord(job: JsonRecord): JsonRecord | null {
  if (!hasOwnField(job, "progress")) return null;
  if (isRecord(job.progress)) return job.progress;
  throw new Error("Sir Convert transcript field 'progress' is not an object.");
}

function parseProgressSnapshot(
  job: JsonRecord,
  status: SirConvertJobStatus,
): SirConvertTranscriptProgressSnapshot {
  const progress = progressRecord(job);
  if (!progress) {
    if (status === "running" || status === "processing") {
      throw new Error("Running Sir Convert transcript job is missing progress.");
    }
    return emptyProgress(status);
  }
  const processedMediaSeconds = readNullableNonNegativeNumber(
    progress.audio_processed_media_seconds,
    "audio_processed_media_seconds",
  );
  const totalMediaSeconds = readNullableNonNegativeNumber(
    progress.audio_total_media_seconds,
    "audio_total_media_seconds",
  );
  if (
    processedMediaSeconds !== null &&
    totalMediaSeconds !== null &&
    processedMediaSeconds > totalMediaSeconds
  ) {
    throw new Error("Transcript processed media seconds exceed total media seconds.");
  }
  const currentChunkIndex = readNullableNonNegativeInteger(
    progress.audio_current_chunk_index,
    "audio_current_chunk_index",
  );
  const totalChunks = readNullableNonNegativeInteger(
    progress.audio_total_chunks,
    "audio_total_chunks",
  );
  if (currentChunkIndex !== null && totalChunks !== null && currentChunkIndex >= totalChunks) {
    throw new Error("Transcript current chunk index exceeds total chunk count.");
  }
  return {
    status,
    phase: readProgressPhase(progress.stage, "progress.stage"),
    lastHeartbeatAt: readNullableDateTime(progress.last_heartbeat_at, "last_heartbeat_at"),
    currentPhaseStartedAt: readNullableDateTime(
      progress.current_phase_started_at,
      "current_phase_started_at",
    ),
    processedMediaSeconds,
    totalMediaSeconds,
    percentComplete: readNullablePercent(
      progress.audio_percent_complete,
      "audio_percent_complete",
    ),
    currentChunkIndex,
    totalChunks,
    phaseTimingsMs: parsePhaseTimings(progress.phase_timings_ms),
  };
}

export function parseTranscriptJob(payload: unknown): SirConvertTranscriptJob {
  const root = readRecord(payload, "payload");
  const job = isRecord(root.job)
    ? root.job
    : ({
        job_id: root.job_id,
        status: root.status,
        ...(hasOwnField(root, "progress") ? { progress: root.progress } : {}),
      } satisfies JsonRecord);
  const status = readStatus(job.status);
  return {
    jobId: readString(job.job_id, "job.job_id"),
    status,
    progress: parseProgressSnapshot(job, status),
  };
}

function parseTranscriptResultJob(payload: unknown, root: JsonRecord): SirConvertTranscriptJob {
  if (isRecord(root.job) || typeof root.status === "string") {
    return parseTranscriptJob(payload);
  }
  return {
    jobId: readString(root.job_id, "job_id"),
    status: "succeeded",
    progress: emptyProgress("succeeded"),
  };
}

function readTranscriptPipeline(value: unknown): "audio_to_transcript_bundle_v2" {
  const pipelineUsed = readString(value, "conversion_metadata.pipeline_used");
  if (pipelineUsed === "audio_to_transcript_bundle_v2") {
    return pipelineUsed;
  }
  throw new Error(`Unknown Sir Convert transcript pipeline '${pipelineUsed}'.`);
}

function readTranscriptApiVersion(value: unknown): "v2" {
  const apiVersion = readString(value, "api_version");
  if (apiVersion === "v2") {
    return apiVersion;
  }
  throw new Error(`Unknown Sir Convert transcript API version '${apiVersion}'.`);
}

function parseArtifactEntry(payload: unknown): SirConvertTranscriptArtifactEntry {
  const entry = readRecord(payload, "artifact");
  const artifactKey = readArtifactKey(entry.artifact_key);
  const availability = readAvailability(entry.availability);
  const unavailableCode =
    typeof entry.unavailable_code === "string" && entry.unavailable_code.length > 0
      ? entry.unavailable_code
      : undefined;
  if (
    (availability === "unavailable" ||
      availability === "failed" ||
      availability === "unrequested") &&
    !unavailableCode
  ) {
    throw new Error(`Transcript artifact '${artifactKey}' requires unavailable_code.`);
  }
  const retrievalPath =
    typeof entry.retrieval_path === "string" && entry.retrieval_path.length > 0
      ? entry.retrieval_path
      : undefined;
  if (availability !== "available") {
    return {
      artifact_key: artifactKey,
      availability,
      ...(retrievalPath ? { retrieval_path: retrievalPath } : {}),
      ...(unavailableCode ? { unavailable_code: unavailableCode } : {}),
    };
  }
  const contentType = readString(entry.content_type, "content_type");
  const expectedContentType = SIR_CONVERT_TRANSCRIPT_ARTIFACT_CONTENT_TYPES[artifactKey];
  if (contentType !== expectedContentType) {
    throw new Error(
      `Transcript artifact '${artifactKey}' has content type '${contentType}' instead of '${expectedContentType}'.`,
    );
  }
  return {
    artifact_key: artifactKey,
    filename: readString(entry.filename, "filename"),
    content_type: contentType,
    availability,
    size_bytes: readNullableNumber(entry.size_bytes, "size_bytes"),
    sha256: readNullableString(entry.sha256, "sha256"),
    ...(retrievalPath ? { retrieval_path: retrievalPath } : {}),
    ...(unavailableCode ? { unavailable_code: unavailableCode } : {}),
  };
}

function isFormatterArtifactKey(
  artifactKey: SirConvertTranscriptArtifactKey,
): artifactKey is SirConvertTranscriptFormatterArtifactKey {
  return artifactKey !== "transcript_json";
}

function formatterArtifactsByKey(
  artifacts: SirConvertTranscriptArtifactEntry[],
): Partial<Record<SirConvertTranscriptFormatterArtifactKey, SirConvertTranscriptArtifactEntry>> {
  const formatterArtifacts: Partial<
    Record<SirConvertTranscriptFormatterArtifactKey, SirConvertTranscriptArtifactEntry>
  > = {};
  for (const artifact of artifacts) {
    if (isFormatterArtifactKey(artifact.artifact_key)) {
      formatterArtifacts[artifact.artifact_key] = artifact;
    }
  }
  return formatterArtifacts;
}

function assertUniqueArtifactKeys(artifacts: SirConvertTranscriptArtifactEntry[]): void {
  const seen = new Set<SirConvertTranscriptArtifactKey>();
  for (const artifact of artifacts) {
    if (seen.has(artifact.artifact_key)) {
      throw new Error(`Duplicate Sir Convert transcript artifact key '${artifact.artifact_key}'.`);
    }
    seen.add(artifact.artifact_key);
  }
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
  const outputFormat = readString(root.output_format, "output_format");
  if (outputFormat !== "transcript_bundle") {
    throw new Error(`Unknown Sir Convert transcript output format '${outputFormat}'.`);
  }
  if (!Array.isArray(root.artifacts)) {
    throw new Error("Sir Convert transcript manifest is missing artifacts.");
  }
  const artifacts = root.artifacts.map((entry) => parseArtifactEntry(entry));
  assertUniqueArtifactKeys(artifacts);
  const transcriptJsonArtifact = artifacts.find(
    (entry) => entry.artifact_key === "transcript_json",
  );
  if (!transcriptJsonArtifact) {
    throw new Error("Sir Convert transcript manifest is missing transcript_json.");
  }
  if (transcriptJsonArtifact.availability !== "available") {
    throw new Error("Sir Convert transcript_json artifact is not available.");
  }
  return {
    api_version: readTranscriptApiVersion(root.api_version),
    job_id: readString(root.job_id, "job_id"),
    output_format: "transcript_bundle",
    artifacts,
    transcriptJsonArtifact,
    formatterArtifacts: formatterArtifactsByKey(artifacts),
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
  const usedMode = readNullableString(diarization.used_mode, "diarization.used_mode");
  if (
    diarizationStatus === "failed" ||
    diarizationStatus === "unavailable" ||
    usedMode === "diarization_unavailable"
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

function transcriptSegments(root: JsonRecord, transcript: JsonRecord): unknown {
  if (Array.isArray(root.segments)) {
    return root.segments;
  }
  return transcript.segments;
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
    id: readString(
      segment.id ?? segment.segment_id ?? `segment_${index + 1}`,
      `segments[${index}].id`,
    ),
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
  const rawSegments = transcriptSegments(root, transcript);
  if (!Array.isArray(rawSegments) || rawSegments.length === 0) {
    throw new Error("Transcript JSON is missing non-empty segments.");
  }
  const transcriptText = readString(
    transcript.text ?? root.transcript_text ?? root.text,
    "transcript.text",
  );
  const segments = rawSegments.map((entry, index) => parseSegment(entry, index));
  return {
    rawJson: root,
    schemaVersion: readString(root.schema_version, "schema_version"),
    transcriptText,
    segments,
  };
}
