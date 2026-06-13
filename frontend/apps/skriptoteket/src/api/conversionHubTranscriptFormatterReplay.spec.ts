/**
 * Conversion Hub transcript formatter replay API specs.
 *
 * Domain purpose:
 *   Prove the frontend command asks Skriptoteket for owner-scoped replay input,
 *   submits through HuleEdu Gateway, and records producer artifact refs.
 *
 * Relationships:
 *   - Exercises `conversionHubTranscriptFormatterReplay.ts`.
 *   - Uses a fake Gateway client instead of local formatter logic.
 */

import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { requestConversionHubTranscriptFormatterReplay } from "./conversionHubTranscriptFormatterReplay";
import { useAuthStore } from "../stores/auth";

function jsonResponse(payload: unknown): Response {
  return new Response(JSON.stringify(payload), {
    headers: { "content-type": "application/json" },
    status: 200,
  });
}

function preparedReplay(): Record<string, unknown> {
  return {
    transcript_id: "saved-transcript-1",
    correlation_id: "corr-replay-1",
    idempotency_key: "idem-replay-1",
    gateway_filename: "saved-transcript-1.json",
    content_type: "application/json",
    transcript_json: { schema_version: "transcript_json_v1" },
    job_spec: {
      api_version: "v2",
      source: { kind: "upload", filename: "saved-transcript-1.json", format: "transcript_json" },
      conversion: { output_format: "transcript_bundle" },
      transcript_formatter_options: {
        schema_version: "transcript_formatter_replay_v1",
        requested_artifacts: ["txt", "md"],
        speaker_label_overrides: [
          { canonical_speaker_label: "SPEAKER_00", display_name: "Anna Andersson" },
        ],
      },
      retention: { pin: false },
    },
  };
}

function completedReplay(): Record<string, unknown> {
  return {
    transcript_id: "saved-transcript-1",
    conversion_hub_job_id: "local-replay-job-1",
    sir_convert_job_id: "sir-replay-job-1",
    correlation_id: "corr-replay-1",
    status: "succeeded",
    requested_artifacts: ["txt", "md"],
    artifacts: [
      {
        requested_artifact: "txt",
        artifact_key: "transcript_txt",
        filename: "transcript_txt.txt",
        content_type: "text/plain",
        size_bytes: 12,
        sha256: "txt",
        retrieval_path: "/v2/convert/jobs/sir-replay-job-1/artifacts/transcript_txt",
      },
    ],
  };
}

describe("conversionHubTranscriptFormatterReplay", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.mocked(fetch).mockReset();
    const auth = useAuthStore();
    auth.csrfToken = "csrf-token";
  });

  it("prepares, submits, parses, and records replay refs without local formatting", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(jsonResponse(preparedReplay()))
      .mockResolvedValueOnce(jsonResponse(completedReplay()));
    const rawResult = {
      result: {
        artifact: {
          content_type: "application/json",
          filename: "transcript_replay_bundle_manifest.json",
          format: "transcript_bundle",
          sha256: "bundle",
          size_bytes: 42,
        },
        conversion_metadata: {
          acceleration_used: null,
          backend_used: null,
          options_fingerprint: "sha256:abc",
          pipeline_used: "transcript_json_to_transcript_bundle_replay_v2",
        },
      },
    };
    const rawManifest = {
      api_version: "v2",
      artifacts: [],
      job_id: "sir-replay-job-1",
      output_format: "transcript_bundle",
    };
    const gatewayClient = {
      getTranscriptFormatterReplayResult: vi.fn().mockResolvedValue({
        artifact: {
          content_type: "application/json",
          filename: "transcript_replay_bundle_manifest.json",
          format: "transcript_bundle",
          sha256: "bundle",
          size_bytes: 42,
        },
        conversion_metadata: {
          acceleration_used: null,
          backend_used: null,
          options_fingerprint: "sha256:abc",
          pipeline_used: "transcript_json_to_transcript_bundle_replay_v2",
        },
        rawResult,
      }),
      getTranscriptJob: vi.fn(),
      listTranscriptFormatterReplayArtifacts: vi.fn().mockResolvedValue({
        api_version: "v2",
        artifacts: [
          {
            artifact_key: "transcript_txt",
            availability: "available",
            content_type: "text/plain",
            filename: "transcript_txt.txt",
            size_bytes: 12,
            sha256: "txt",
            retrieval_path: "/v2/convert/jobs/sir-replay-job-1/artifacts/transcript_txt",
          },
          {
            artifact_key: "transcript_md",
            availability: "available",
            content_type: "text/markdown",
            filename: "transcript_md.md",
            size_bytes: 24,
            sha256: "md",
            retrieval_path: "/v2/convert/jobs/sir-replay-job-1/artifacts/transcript_md",
          },
        ],
        formatterArtifacts: {
          transcript_md: undefined,
          transcript_srt: undefined,
          transcript_txt: undefined,
          transcript_vtt: undefined,
        },
        job_id: "sir-replay-job-1",
        output_format: "transcript_bundle",
        rawManifest,
      }),
      submitTranscriptFormatterReplay: vi.fn().mockResolvedValue({
        jobId: "sir-replay-job-1",
        status: "succeeded",
      }),
    };

    const result = await requestConversionHubTranscriptFormatterReplay({
      gatewayClient,
      requestedArtifacts: ["txt", "md"],
      transcriptId: "saved-transcript-1",
    });

    expect(result.conversion_hub_job_id).toBe("local-replay-job-1");
    expect(gatewayClient.submitTranscriptFormatterReplay).toHaveBeenCalledWith(
      expect.objectContaining({
        correlationId: "corr-replay-1",
        idempotencyKey: "idem-replay-1",
        requestedArtifacts: ["txt", "md"],
      }),
    );
    expect(fetch).toHaveBeenNthCalledWith(
      1,
      "/api/v1/apps/documents.conversion_hub/transcripts/saved-transcript-1/formatter-replay/prepare",
      expect.objectContaining({ method: "POST" }),
    );
    expect(fetch).toHaveBeenNthCalledWith(
      2,
      "/api/v1/apps/documents.conversion_hub/transcripts/saved-transcript-1/formatter-replay/complete",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("does not record completion when Gateway artifact parsing fails", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse(preparedReplay()));
    const gatewayClient = {
      getTranscriptFormatterReplayResult: vi.fn().mockResolvedValue({
        artifact: {
          content_type: "application/json",
          filename: "transcript_replay_bundle_manifest.json",
          format: "transcript_bundle",
          sha256: "bundle",
          size_bytes: 42,
        },
        conversion_metadata: {
          acceleration_used: null,
          backend_used: null,
          options_fingerprint: "sha256:abc",
          pipeline_used: "transcript_json_to_transcript_bundle_replay_v2",
        },
        rawResult: {},
      }),
      getTranscriptJob: vi.fn(),
      listTranscriptFormatterReplayArtifacts: vi
        .fn()
        .mockRejectedValue(new Error("missing requested")),
      submitTranscriptFormatterReplay: vi.fn().mockResolvedValue({
        jobId: "sir-replay-job-1",
        status: "succeeded",
      }),
    };

    await expect(
      requestConversionHubTranscriptFormatterReplay({
        gatewayClient,
        requestedArtifacts: ["txt", "md"],
        transcriptId: "saved-transcript-1",
      }),
    ).rejects.toThrow("missing requested");

    expect(fetch).toHaveBeenCalledTimes(1);
  });
});
