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

import type { SirConvertArtifactAvailability, SirConvertJobStatus } from "./types";

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
  output_artifacts: ["json"];
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
  file: File;
  speakerControl: TranscriptSpeakerControl;
  language?: AudioTranscriptionOptions["language"];
  waitSeconds?: number;
  correlationId?: string | null;
  sourceLabel?: string | null;
};

export type SirConvertTranscriptRequestContext = {
  correlationId: string;
  idempotencyKey: string;
  jobSpec: SirConvertTranscriptJobSpec;
};

export type SirConvertTranscriptAudioProgress = {
  totalMediaSeconds: number | null;
  processedMediaSeconds: number | null;
  percentComplete: number | null;
  currentChunkIndex: number | null;
  totalChunks: number | null;
};

export type SirConvertTranscriptJob = {
  jobId: string;
  status: SirConvertJobStatus;
  stage: string | null;
  audioProgress: SirConvertTranscriptAudioProgress;
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
  artifact_key: string;
  filename: string;
  content_type: string;
  availability: SirConvertArtifactAvailability;
  size_bytes: number | null;
  sha256: string | null;
  download_path?: string;
  unavailable_code?: string;
};

export type SirConvertTranscriptArtifactManifest = {
  schema_version: string;
  job_id: string;
  source: {
    filename: string;
    sha256: string;
    format: "audio";
  };
  bundle_status: string;
  artifacts: SirConvertTranscriptArtifactEntry[];
  transcriptJsonArtifact: SirConvertTranscriptArtifactEntry | null;
};

export type TranscriptSegment = {
  id: string;
  startSeconds: number;
  endSeconds: number;
  speakerLabel: string;
  text: string;
};

export type TranscriptJson = {
  schemaVersion: string;
  transcriptText: string;
  segments: TranscriptSegment[];
};

export type SirConvertTranscriptCancelResult = SirConvertTranscriptJob;
