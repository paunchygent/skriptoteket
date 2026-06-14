/**
 * Sir Convert transcript Gateway contracts.
 *
 * Purpose:
 *   Define Skriptoteket's typed consumer protocol for authenticated
 *   `audio -> transcript_bundle` jobs through HuleEdu Gateway.
 *
 * Relationships:
 *   - `transcriptOptions.ts` builds request values from teacher controls.
 *   - `transcriptParsers.ts` validates lifecycle and `transcript_json`
 *     responses before UI consumption.
 */

import type { SirConvertJobStatus } from "./types";
import type { SirConvertUploadProgressHandler } from "./uploadProgress";

export const SIR_CONVERT_TRANSCRIPT_OUTPUT_ARTIFACTS = [
  "json",
  "txt",
  "md",
  "vtt",
  "srt",
] as const;

export type SirConvertTranscriptOutputArtifact =
  (typeof SIR_CONVERT_TRANSCRIPT_OUTPUT_ARTIFACTS)[number];

export type SirConvertTranscriptOutputArtifacts = readonly [
  SirConvertTranscriptOutputArtifact,
  ...SirConvertTranscriptOutputArtifact[],
];

export const SIR_CONVERT_TRANSCRIPT_ARTIFACT_KEYS = [
  "transcript_json",
  "transcript_txt",
  "transcript_md",
  "transcript_vtt",
  "transcript_srt",
] as const;

export type SirConvertTranscriptArtifactKey =
  (typeof SIR_CONVERT_TRANSCRIPT_ARTIFACT_KEYS)[number];

export const SIR_CONVERT_TRANSCRIPT_FORMATTER_ARTIFACT_KEYS = [
  "transcript_txt",
  "transcript_md",
  "transcript_vtt",
  "transcript_srt",
] as const;

export type SirConvertTranscriptFormatterArtifactKey =
  (typeof SIR_CONVERT_TRANSCRIPT_FORMATTER_ARTIFACT_KEYS)[number];

export const SIR_CONVERT_TRANSCRIPT_ARTIFACT_KEY_BY_OUTPUT_ARTIFACT = {
  json: "transcript_json",
  txt: "transcript_txt",
  md: "transcript_md",
  vtt: "transcript_vtt",
  srt: "transcript_srt",
} as const satisfies Record<
  SirConvertTranscriptOutputArtifact,
  SirConvertTranscriptArtifactKey
>;

export const SIR_CONVERT_TRANSCRIPT_ARTIFACT_CONTENT_TYPES = {
  transcript_json: "application/json",
  transcript_txt: "text/plain",
  transcript_md: "text/markdown",
  transcript_vtt: "text/vtt",
  transcript_srt: "application/x-subrip",
} as const satisfies Record<SirConvertTranscriptArtifactKey, string>;

export const SIR_CONVERT_TRANSCRIPT_ARTIFACT_AVAILABILITIES = [
  "available",
  "unavailable",
  "failed",
  "unrequested",
] as const;

export type SirConvertTranscriptArtifactAvailability =
  (typeof SIR_CONVERT_TRANSCRIPT_ARTIFACT_AVAILABILITIES)[number];

export type TranscriptSpeakerControl =
  | { mode: "auto" }
  | { mode: "known_speaker_count"; speakerCount: number }
  | { mode: "speaker_range"; minSpeakers: number; maxSpeakers: number };

export type TranscriptDiarizationOptions = {
  mode: TranscriptSpeakerControl["mode"];
  num_speakers: number | null;
  min_speakers: number | null;
  max_speakers: number | null;
};

export type AudioTranscriptionOptions = {
  language: "auto" | "sv" | "en";
  diarization: TranscriptDiarizationOptions;
  max_duration_seconds: 7200;
  output_artifacts: SirConvertTranscriptOutputArtifacts;
};

export type SirConvertTranscriptJobSpec = {
  api_version: "v2";
  source: {
    kind: "upload";
    filename: string;
    format: "audio";
  };
  conversion: {
    output_format: "transcript_bundle";
  };
  audio_transcription_options: AudioTranscriptionOptions;
  execution: {
    acceleration_policy: "gpu_required";
    priority: "normal";
    document_timeout_seconds: 7200;
  };
  retention: {
    pin: false;
  };
};

export type TranscriptSubmitParams = {
  abortSignal?: AbortSignal;
  file: File;
  speakerControl: TranscriptSpeakerControl;
  language?: AudioTranscriptionOptions["language"];
  onUploadProgress?: SirConvertUploadProgressHandler;
  waitSeconds?: number;
  correlationId?: string | null;
  sourceLabel?: string | null;
  outputArtifacts?: SirConvertTranscriptOutputArtifacts;
};

export type SirConvertTranscriptRequestContext = {
  correlationId: string;
  idempotencyKey: string;
  jobSpec: SirConvertTranscriptJobSpec;
};

export const SIR_CONVERT_TRANSCRIPT_PROGRESS_PHASES = [
  "submitted",
  "queued",
  "starting",
  "probing_media",
  "normalizing_audio",
  "transcribing",
  "diarizing",
  "aligning_segments",
  "packaging",
  "succeeded",
  "failed",
  "canceled",
  "cancelled",
] as const;

export type SirConvertTranscriptProgressPhase =
  (typeof SIR_CONVERT_TRANSCRIPT_PROGRESS_PHASES)[number];

export const SIR_CONVERT_TRANSCRIPT_PHASE_TIMING_KEYS = [
  "audio_probe_normalize_ms",
  "audio_diarization_ms",
  "audio_transcription_ms",
  "audio_alignment_ms",
  "audio_packaging_ms",
  "ocr_layout_extract_ms",
  "markdown_normalize_ms",
  "formula_enrichment_ms",
  "checkpoint_persist_ms",
  "final_artifact_persist_ms",
  "chunk_total_ms",
  "conversion_total_ms",
] as const;

export type SirConvertTranscriptPhaseTimingKey =
  (typeof SIR_CONVERT_TRANSCRIPT_PHASE_TIMING_KEYS)[number];

export type SirConvertTranscriptProgressSnapshot = {
  status: SirConvertJobStatus;
  phase: SirConvertTranscriptProgressPhase | null;
  lastHeartbeatAt: string | null;
  currentPhaseStartedAt: string | null;
  processedMediaSeconds: number | null;
  totalMediaSeconds: number | null;
  percentComplete: number | null;
  audioPipelinePercentComplete: number | null;
  audioPipelineEtaSeconds: number | null;
  currentChunkIndex: number | null;
  totalChunks: number | null;
  phaseTimingsMs: Partial<Record<SirConvertTranscriptPhaseTimingKey, number>>;
};

export type SirConvertTranscriptJob = {
  jobId: string;
  status: SirConvertJobStatus;
  progress: SirConvertTranscriptProgressSnapshot;
};

export type SirConvertTranscriptSubmittedJob = SirConvertTranscriptJob & {
  idempotentReplay: boolean;
  requestContext: SirConvertTranscriptRequestContext;
};

export type SirConvertTranscriptTerminalResult = {
  job: SirConvertTranscriptJob;
  artifact: {
    filename: string;
    content_type: string;
    sha256: string | null;
    size_bytes: number | null;
  };
  conversion_metadata: {
    pipeline_used: "audio_to_transcript_bundle_v2";
    backend_used: string;
    acceleration_used: string;
    options_fingerprint: string;
  };
};

export type SirConvertTranscriptArtifactEntry = {
  artifact_key: SirConvertTranscriptArtifactKey;
  availability: SirConvertTranscriptArtifactAvailability;
  filename?: string;
  content_type?: string;
  size_bytes?: number | null;
  sha256?: string | null;
  retrieval_path?: string;
  unavailable_code?: string;
};

export type SirConvertTranscriptArtifactManifest = {
  api_version: "v2";
  job_id: string;
  output_format: "transcript_bundle";
  artifacts: SirConvertTranscriptArtifactEntry[];
  transcriptJsonArtifact: SirConvertTranscriptArtifactEntry;
  formatterArtifacts: Partial<
    Record<SirConvertTranscriptFormatterArtifactKey, SirConvertTranscriptArtifactEntry>
  >;
};

export type TranscriptSegment = {
  id: string;
  startSeconds: number;
  endSeconds: number;
  speakerLabel: string;
  text: string;
};

export type TranscriptJson = {
  rawJson?: Record<string, unknown>;
  schemaVersion: string;
  transcriptText: string;
  segments: TranscriptSegment[];
};

export type SirConvertTranscriptCancelResult = SirConvertTranscriptJob;
