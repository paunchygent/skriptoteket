/**
 * Conversion Hub transcript save client specs.
 *
 * Domain purpose:
 *   Prove the frontend sends canonical transcript JSON and provenance to the
 *   durable Skriptoteket transcript save boundary.
 *
 * Relationships:
 *   - Exercises `conversionHubTranscriptSaves.ts`.
 *   - Complements backend PR-0343 API route tests.
 */

import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  buildSaveTranscriptRequest,
  getConversionHubTranscriptSpeakerOverlays,
  registerTranscriptConversionHubJob,
  saveConversionHubTranscript,
  updateConversionHubTranscriptSpeakerOverlays,
} from "./conversionHubTranscriptSaves";
import { useAuthStore } from "../stores/auth";

function jsonResponse(payload: unknown): Response {
  return new Response(JSON.stringify(payload), {
    headers: { "content-type": "application/json" },
    status: 200,
  });
}

describe("conversionHubTranscriptSaves", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.mocked(fetch).mockReset();
    const auth = useAuthStore();
    auth.csrfToken = "csrf-token";
  });

  it("builds a save request from raw canonical JSON and speaker provenance", () => {
    const rawJson = {
      schema_version: "transcript_json_v1",
      transcript: { text: "Hej.", segments: [] },
      language: { detected: "sv" },
      runtime: { generated_at: "2026-06-12T10:00:00Z" },
      vendor_extension: { preserved: true },
    };
    const request = buildSaveTranscriptRequest({
      correlationId: "corr-transcript-1",
      sirConvertJobId: "sir-transcript-job-1",
      sourceFilename: "seminarium.m4a",
      speakerControl: { mode: "speaker_range", minSpeakers: 2, maxSpeakers: 4 },
      transcript: {
        rawJson,
        schemaVersion: "transcript_json_v1",
        transcriptText: "Hej.",
        segments: [],
      },
    });

    expect(request).toMatchObject({
      artifact_key: "transcript_json",
      correlation_id: "corr-transcript-1",
      diarization_mode: "speaker_range",
      generated_at: "2026-06-12T10:00:00Z",
      language_code: "sv",
      speaker_count: null,
      speaker_max: 4,
      speaker_min: 2,
      transcript_json: { schema_version: "transcript_json_v1" },
    });
    expect(request.transcript_json).toBe(rawJson);
  });

  it("registers and saves through the Conversion Hub transcript routes", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(
        jsonResponse({
          job_id: "local-job-1",
          upstream_job_id: "sir-transcript-job-1",
          status: "succeeded",
        }),
      )
      .mockResolvedValueOnce(
        jsonResponse({
          transcript_id: "saved-transcript-1",
          owner_user_id: "owner-1",
          conversion_hub_job_id: "local-job-1",
          sir_convert_job_id: "sir-transcript-job-1",
          artifact_key: "transcript_json",
          source_filename: "seminarium.m4a",
          transcript_schema_version: "transcript_json_v1",
          language_code: "sv",
          diarization_mode: "known_speaker_count",
          speaker_count: 2,
          speaker_min: null,
          speaker_max: null,
          generated_at: null,
          correlation_id: "corr-transcript-1",
          transcript_json: { schema_version: "transcript_json_v1" },
          created_at: "2026-06-12T10:05:00Z",
          updated_at: "2026-06-12T10:05:00Z",
        }),
      );

    await registerTranscriptConversionHubJob({
      request: {
        upstream_job_id: "sir-transcript-job-1",
        input_filename: "seminarium.m4a",
        correlation_id: "corr-transcript-1",
        status: "succeeded",
      },
    });
    await saveConversionHubTranscript({
      conversionHubJobId: "local-job-1",
      request: {
        sir_convert_job_id: "sir-transcript-job-1",
        artifact_key: "transcript_json",
        source_filename: "seminarium.m4a",
        transcript_json: { schema_version: "transcript_json_v1" },
        transcript_schema_version: "transcript_json_v1",
        language_code: "sv",
        diarization_mode: "known_speaker_count",
        speaker_count: 2,
        speaker_min: null,
        speaker_max: null,
        generated_at: null,
        correlation_id: "corr-transcript-1",
      },
    });

    expect(fetch).toHaveBeenNthCalledWith(
      1,
      "/api/v1/apps/documents.conversion_hub/transcripts/jobs",
      expect.objectContaining({ method: "POST" }),
    );
    expect(fetch).toHaveBeenNthCalledWith(
      2,
      "/api/v1/apps/documents.conversion_hub/transcripts/jobs/local-job-1",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("reads and replaces saved transcript speaker overlays through typed routes", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(
        jsonResponse({
          transcript_id: "saved-transcript-1",
          overlays: [
            {
              canonical_speaker_label: "SPEAKER_00",
              display_name: "Anna Andersson",
            },
          ],
          updated_at: "2026-06-12T11:00:00Z",
        }),
      )
      .mockResolvedValueOnce(
        jsonResponse({
          transcript_id: "saved-transcript-1",
          overlays: [
            {
              canonical_speaker_label: "SPEAKER_00",
              display_name: "Bo Berg",
            },
          ],
          updated_at: "2026-06-12T11:05:00Z",
        }),
      );

    await getConversionHubTranscriptSpeakerOverlays({
      transcriptId: "saved-transcript-1",
    });
    await updateConversionHubTranscriptSpeakerOverlays({
      transcriptId: "saved-transcript-1",
      request: {
        overlays: [
          {
            canonical_speaker_label: "SPEAKER_00",
            display_name: "Bo Berg",
          },
        ],
      },
    });

    expect(fetch).toHaveBeenNthCalledWith(
      1,
      "/api/v1/apps/documents.conversion_hub/transcripts/saved-transcript-1/speaker-overlays",
      expect.objectContaining({ method: "GET" }),
    );
    expect(fetch).toHaveBeenNthCalledWith(
      2,
      "/api/v1/apps/documents.conversion_hub/transcripts/saved-transcript-1/speaker-overlays",
      expect.objectContaining({ method: "PUT" }),
    );
  });
});
