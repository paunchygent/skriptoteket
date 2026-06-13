/**
 * Sir Convert transcript request values.
 *
 * Purpose:
 *   Convert teacher-facing transcript controls into the accepted
 *   `audio -> transcript_bundle` JobSpec without exposing backend knobs.
 *
 * Relationships:
 *   - `transcriptRequestContext.ts` fingerprints the JobSpec for headers.
 *   - `client.ts` serializes this shape as multipart Gateway traffic.
 */

import { SirConvertGatewayError } from "./errors";
import type {
  AudioTranscriptionOptions,
  SirConvertTranscriptOutputArtifact,
  SirConvertTranscriptOutputArtifacts,
  SirConvertTranscriptJobSpec,
  TranscriptSpeakerControl,
  TranscriptSubmitParams,
} from "./transcriptTypes";

const MAX_AUDIO_UPLOAD_BYTES = 500 * 1024 * 1024;
const ACCEPTED_AUDIO_EXTENSIONS = new Set([
  ".wav",
  ".mp3",
  ".m4a",
  ".aac",
  ".flac",
  ".ogg",
  ".opus",
  ".webm",
  ".aiff",
  ".mp4",
  ".mov",
  ".mkv",
]);

type MutableTranscriptOutputArtifacts = [
  SirConvertTranscriptOutputArtifact,
  ...SirConvertTranscriptOutputArtifact[],
];

function gatewayInputError(code: string, message: string): SirConvertGatewayError {
  return new SirConvertGatewayError({ code, message, status: 0 });
}

function isPositiveInteger(value: number): boolean {
  return Number.isSafeInteger(value) && value >= 1;
}

function validateTranscriptFile(file: File): void {
  const filename = file.name.toLowerCase();
  const extension = filename.includes(".") ? filename.slice(filename.lastIndexOf(".")) : "";
  if (!ACCEPTED_AUDIO_EXTENSIONS.has(extension)) {
    throw gatewayInputError(
      "INVALID_TRANSCRIPT_SOURCE",
      "Choose an audio or video file with an audio track.",
    );
  }
  if (file.size > MAX_AUDIO_UPLOAD_BYTES) {
    throw gatewayInputError(
      "TRANSCRIPT_UPLOAD_TOO_LARGE",
      "Audio and video transcript uploads must be 500 MiB or smaller.",
    );
  }
}

function buildDiarizationOptions(
  control: TranscriptSpeakerControl,
): AudioTranscriptionOptions["diarization"] {
  if (control.mode === "auto") {
    return {
      mode: "auto",
      num_speakers: null,
      min_speakers: null,
      max_speakers: null,
    };
  }
  if (control.mode === "known_speaker_count") {
    if (!isPositiveInteger(control.speakerCount)) {
      throw gatewayInputError(
        "INVALID_TRANSCRIPT_SPEAKER_COUNT",
        "Known speaker count must be at least 1.",
      );
    }
    return {
      mode: "known_speaker_count",
      num_speakers: control.speakerCount,
      min_speakers: null,
      max_speakers: null,
    };
  }
  if (!isPositiveInteger(control.minSpeakers) || !isPositiveInteger(control.maxSpeakers)) {
    throw gatewayInputError(
      "INVALID_TRANSCRIPT_SPEAKER_RANGE",
      "Speaker range must use positive whole numbers.",
    );
  }
  if (control.maxSpeakers < control.minSpeakers) {
    throw gatewayInputError(
      "INVALID_TRANSCRIPT_SPEAKER_RANGE",
      "Maximum speakers must be greater than or equal to minimum speakers.",
    );
  }
  return {
    mode: "speaker_range",
    num_speakers: null,
    min_speakers: control.minSpeakers,
    max_speakers: control.maxSpeakers,
  };
}

function isTranscriptOutputArtifact(value: string): value is SirConvertTranscriptOutputArtifact {
  switch (value) {
    case "json":
    case "txt":
    case "md":
    case "vtt":
    case "srt":
      return true;
    default:
      return false;
  }
}

function normalizeOutputArtifacts(
  artifacts: SirConvertTranscriptOutputArtifacts | undefined,
): SirConvertTranscriptOutputArtifacts {
  const requested = artifacts ?? ["json"];
  const orderedArtifacts: MutableTranscriptOutputArtifacts = ["json"];
  for (const artifact of requested) {
    if (!isTranscriptOutputArtifact(artifact)) {
      throw gatewayInputError(
        "INVALID_TRANSCRIPT_OUTPUT_ARTIFACT",
        "Transcript output artifact is not supported.",
      );
    }
    if (!orderedArtifacts.includes(artifact)) {
      orderedArtifacts.push(artifact);
    }
  }
  return orderedArtifacts;
}

export function buildAudioTranscriptionOptions(params: {
  language?: AudioTranscriptionOptions["language"];
  speakerControl: TranscriptSpeakerControl;
  outputArtifacts?: SirConvertTranscriptOutputArtifacts;
}): AudioTranscriptionOptions {
  return {
    language: params.language ?? "auto",
    diarization: buildDiarizationOptions(params.speakerControl),
    max_duration_seconds: 7200,
    output_artifacts: normalizeOutputArtifacts(params.outputArtifacts),
  };
}

export function buildTranscriptJobSpec(
  params: TranscriptSubmitParams,
): SirConvertTranscriptJobSpec {
  validateTranscriptFile(params.file);
  return {
    api_version: "v2",
    source: {
      kind: "upload",
      filename: params.file.name,
      format: "audio",
    },
    conversion: {
      output_format: "transcript_bundle",
    },
    audio_transcription_options: buildAudioTranscriptionOptions({
      language: params.language,
      outputArtifacts: params.outputArtifacts,
      speakerControl: params.speakerControl,
    }),
    execution: {
      acceleration_policy: "gpu_required",
      priority: "normal",
      document_timeout_seconds: 7200,
    },
    retention: {
      pin: false,
    },
  };
}
