/**
 * Transcript speaker option mapping specs.
 *
 * Domain purpose:
 *   Prove teacher-facing transcript speaker controls map to Sir Convert's
 *   governed audio transcription options before any browser submit happens.
 *
 * Relationships:
 *   - Exercises `transcriptOptions.ts`, which feeds the transcript JobSpec.
 *   - Complements transport coverage in `transcriptClient.spec.ts`.
 */

import { describe, expect, it } from "vitest";

import { SirConvertGatewayError } from "./errors";
import {
  buildAudioTranscriptionOptions,
  buildTranscriptJobSpec,
} from "./transcriptOptions";

function audioFile(name = "seminarium.m4a"): File {
  return new File(["audio"], name, { type: "audio/mp4" });
}

describe("Sir Convert transcript speaker options", () => {
  it("maps automatic speaker discovery to null speaker hints", () => {
    expect(
      buildAudioTranscriptionOptions({ speakerControl: { mode: "auto" } }),
    ).toEqual({
      language: "auto",
      diarization: {
        mode: "auto",
        num_speakers: null,
        min_speakers: null,
        max_speakers: null,
      },
      max_duration_seconds: 7200,
      output_artifacts: ["json"],
    });
  });

  it("maps exact and range controls to Sir Convert diarization fields", () => {
    expect(
      buildAudioTranscriptionOptions({
        speakerControl: { mode: "known_speaker_count", speakerCount: 3 },
      }).diarization,
    ).toEqual({
      mode: "known_speaker_count",
      num_speakers: 3,
      min_speakers: null,
      max_speakers: null,
    });
    expect(
      buildAudioTranscriptionOptions({
        speakerControl: { maxSpeakers: 5, minSpeakers: 2, mode: "speaker_range" },
      }).diarization,
    ).toEqual({
      mode: "speaker_range",
      num_speakers: null,
      min_speakers: 2,
      max_speakers: 5,
    });
  });

  it("normalizes accepted formatter artifact requests while keeping transcript_json required", () => {
    expect(
      buildAudioTranscriptionOptions({
        outputArtifacts: ["txt", "srt"],
        speakerControl: { mode: "auto" },
      }).output_artifacts,
    ).toEqual(["json", "txt", "srt"]);

    expect(
      buildAudioTranscriptionOptions({
        outputArtifacts: ["json", "md", "json"],
        speakerControl: { mode: "auto" },
      }).output_artifacts,
    ).toEqual(["json", "md"]);
  });

  it("rejects invalid speaker combinations before submit", () => {
    expect(() =>
      buildAudioTranscriptionOptions({
        speakerControl: { mode: "known_speaker_count", speakerCount: 0 },
      }),
    ).toThrow(SirConvertGatewayError);
    expect(() =>
      buildAudioTranscriptionOptions({
        speakerControl: { maxSpeakers: 1, minSpeakers: 3, mode: "speaker_range" },
      }),
    ).toThrow(SirConvertGatewayError);
  });

  it("builds only the accepted audio to transcript bundle JobSpec", () => {
    expect(
      buildTranscriptJobSpec({
        file: audioFile("lektion.webm"),
        speakerControl: { mode: "auto" },
      }),
    ).toEqual({
      api_version: "v2",
      source: {
        kind: "upload",
        filename: "lektion.webm",
        format: "audio",
      },
      conversion: {
        output_format: "transcript_bundle",
      },
      audio_transcription_options: {
        language: "auto",
        diarization: {
          mode: "auto",
          num_speakers: null,
          min_speakers: null,
          max_speakers: null,
        },
        max_duration_seconds: 7200,
        output_artifacts: ["json"],
      },
      execution: {
        acceleration_policy: "gpu_required",
        priority: "normal",
        document_timeout_seconds: 7200,
      },
      retention: {
        pin: false,
      },
    });
  });

  it("carries accepted output artifact selection into the JobSpec", () => {
    expect(
      buildTranscriptJobSpec({
        file: audioFile("lektion.m4a"),
        outputArtifacts: ["txt", "md", "vtt", "srt"],
        speakerControl: { mode: "auto" },
      }).audio_transcription_options.output_artifacts,
    ).toEqual(["json", "txt", "md", "vtt", "srt"]);
  });
});
