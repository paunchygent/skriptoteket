/**
 * Sir Convert transcript progress parsers.
 *
 * Domain purpose:
 *   Decode transcript lifecycle progress from Sir Convert, including observed
 *   chunk facts and Task-364 pipeline estimates for teacher-facing progress.
 *
 * Relationships:
 *   - Used by `transcriptParsers.ts` while decoding transcript job responses.
 *   - Shares primitive readers with `transcriptParserScalars.ts`.
 */

import type { SirConvertJobStatus } from "./transcriptTypes";
import {
  hasOwnField,
  isRecord,
  readNullableDateTime,
  readNullableNonNegativeInteger,
  readNullableNonNegativeNumber,
  readNullablePercent,
  readRecord,
  readString,
  type JsonRecord,
} from "./transcriptParserScalars";
import type {
  SirConvertTranscriptPhaseTimingKey,
  SirConvertTranscriptProgressPhase,
  SirConvertTranscriptProgressSnapshot,
} from "./transcriptTypes";

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
    case "audio_probe_normalize_ms":
    case "audio_diarization_ms":
    case "audio_transcription_ms":
    case "audio_alignment_ms":
    case "audio_packaging_ms":
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
    parsed[readPhaseTimingKey(key)] =
      readNullableNonNegativeInteger(timingValue, `phase_timings_ms.${key}`) ?? 0;
  }
  return parsed;
}

export function emptyTranscriptProgress(
  status: SirConvertJobStatus,
): SirConvertTranscriptProgressSnapshot {
  return {
    status,
    phase: null,
    lastHeartbeatAt: null,
    currentPhaseStartedAt: null,
    processedMediaSeconds: null,
    totalMediaSeconds: null,
    percentComplete: null,
    audioPipelinePercentComplete: null,
    audioPipelineEtaSeconds: null,
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

export function parseTranscriptProgressSnapshot(
  job: JsonRecord,
  status: SirConvertJobStatus,
): SirConvertTranscriptProgressSnapshot {
  const progress = progressRecord(job);
  if (!progress) {
    if (status === "running" || status === "processing") {
      throw new Error("Running Sir Convert transcript job is missing progress.");
    }
    return emptyTranscriptProgress(status);
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
    audioPipelinePercentComplete: readNullablePercent(
      progress.audio_pipeline_percent_complete,
      "audio_pipeline_percent_complete",
    ),
    audioPipelineEtaSeconds: readNullableNonNegativeInteger(
      progress.audio_pipeline_eta_seconds,
      "audio_pipeline_eta_seconds",
    ),
    currentChunkIndex,
    totalChunks,
    phaseTimingsMs: parsePhaseTimings(progress.phase_timings_ms),
  };
}
