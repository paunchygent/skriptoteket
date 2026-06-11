/**
 * Transcript Gateway lifecycle specs.
 *
 * Domain purpose:
 *   Prove authenticated transcript submit, status, cancel, artifact discovery,
 *   and canonical JSON parsing through HuleEdu's Sir Convert Gateway edge.
 *
 * Relationships:
 *   - Exercises `client.ts` transcript methods with real request headers.
 *   - Exercises `transcriptParsers.ts` false-success rejection.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";

import { createSirConvertGatewayClient } from "./client";
import { SirConvertGatewayError } from "./errors";

function jsonResponse(payload: unknown, init: ResponseInit = {}): Response {
  const headers = new Headers(init.headers);
  if (!headers.has("content-type")) {
    headers.set("content-type", "application/json");
  }
  return new Response(JSON.stringify(payload), { ...init, headers });
}

function audioFile(): File {
  return new File(["lesson audio"], "lektion.m4a", { type: "audio/mp4" });
}

function validTranscriptJson(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    schema_version: "transcript_json_v1",
    transcript: {
      text: "Hej från lektionen.",
      segments: [
        {
          id: "seg_1",
          start_seconds: 0,
          end_seconds: 3.2,
          speaker_label: "SPEAKER_00",
          text: "Hej från lektionen.",
        },
      ],
    },
    diarization: { status: "succeeded", mode_used: "known_speaker_count" },
    alignment: { status: "succeeded" },
    ...overrides,
  };
}

type FetchMock = ReturnType<typeof vi.fn<typeof fetch>>;

function fetchHeaders(fetcher: FetchMock, index: number): Headers {
  const init = fetcher.mock.calls[index]?.[1] as RequestInit;
  return init.headers as Headers;
}

describe("Sir Convert transcript Gateway client", () => {
  const fetcher = vi.fn<typeof fetch>();
  const client = createSirConvertGatewayClient({
    ensureCsrfToken: async () => "csrf-token",
    fetcher,
  });

  beforeEach(() => {
    fetcher.mockReset();
  });

  it("submits audio through the HuleEdu Gateway with transcript JobSpec and write headers", async () => {
    fetcher.mockResolvedValueOnce(
      jsonResponse(
        { job: { job_id: "job_transcript_1", status: "queued" } },
        { headers: { "X-Idempotent-Replay": "false" } },
      ),
    );

    const submitted = await client.submitTranscriptJob({
      file: audioFile(),
      speakerControl: { mode: "known_speaker_count", speakerCount: 2 },
      waitSeconds: 0,
    });

    expect(submitted.jobId).toBe("job_transcript_1");
    expect(fetcher).toHaveBeenCalledWith(
      "/sir-convert/v2/convert/jobs?wait_seconds=0",
      expect.objectContaining({
        body: expect.any(FormData),
        credentials: "include",
        method: "POST",
      }),
    );
    const headers = fetchHeaders(fetcher, 0);
    expect(headers.get("X-CSRF-Token")).toBe("csrf-token");
    expect(headers.get("Idempotency-Key")).toMatch(/^idem_skriptoteket_[0-9a-f]{48}$/);
    expect(headers.get("X-Correlation-ID")).toMatch(/^corr_skriptoteket_[0-9a-f]{16}$/);
    expect(headers.get("X-API-Key")).toBeNull();

    const body = fetcher.mock.calls[0]?.[1]?.body as FormData;
    expect(body.get("file")).toBeInstanceOf(File);
    expect(JSON.parse(String(body.get("job_spec")))).toMatchObject({
      source: { filename: "lektion.m4a", format: "audio", kind: "upload" },
      conversion: { output_format: "transcript_bundle" },
      audio_transcription_options: {
        diarization: {
          mode: "known_speaker_count",
          num_speakers: 2,
          min_speakers: null,
          max_speakers: null,
        },
        output_artifacts: ["json"],
      },
      retention: { pin: false },
    });
  });

  it("polls status, reads result, lists transcript artifacts, downloads transcript_json, and cancels", async () => {
    fetcher
      .mockResolvedValueOnce(
        jsonResponse({
          job: {
            job_id: "job_transcript_1",
            status: "running",
            progress: {
              stage: "transcribing",
              audio_processed_media_seconds: 42,
              audio_total_media_seconds: 120,
              audio_percent_complete: 35,
              audio_current_chunk_index: 1,
              audio_total_chunks: 3,
            },
          },
        }),
      )
      .mockResolvedValueOnce(
        jsonResponse({
          api_version: "v2",
          job_id: "job_transcript_1",
          result: {
            artifact: {
              filename: "transcript-bundle.json",
              content_type: "application/json",
              sha256: "sha256:abc",
              size_bytes: 512,
            },
            conversion_metadata: {
              pipeline_used: "audio_to_transcript_bundle_v2",
              backend_used: "stt_sidecar",
              acceleration_used: "rocm",
              options_fingerprint: "audio-options-fingerprint",
            },
          },
        }),
      )
      .mockResolvedValueOnce(
        jsonResponse({
          api_version: "v2",
          job_id: "job_transcript_1",
          output_format: "transcript_bundle",
          artifacts: [
            {
              artifact_key: "transcript_json",
              filename: "lektion.transcript.json",
              content_type: "application/json",
              availability: "available",
              size_bytes: 512,
              sha256: "sha256:json",
            },
            {
              artifact_key: "transcript_txt",
              availability: "not_implemented",
              unavailable_code: "audio_transcript_artifact_unavailable",
            },
            {
              artifact_key: "transcript_md",
              availability: "not_implemented",
              unavailable_code: "audio_transcript_artifact_unavailable",
            },
            {
              artifact_key: "transcript_vtt",
              availability: "not_implemented",
              unavailable_code: "audio_transcript_artifact_unavailable",
            },
            {
              artifact_key: "transcript_srt",
              availability: "not_implemented",
              unavailable_code: "audio_transcript_artifact_unavailable",
            },
          ],
        }),
      )
      .mockResolvedValueOnce(
        jsonResponse({
          schema_version: "transcript_json_v1",
          transcript: {
            text: "Hej från lektionen.",
          },
          segments: [
            {
              segment_id: "seg_1",
              start_seconds: 0,
              end_seconds: 3.2,
              speaker_label: "SPEAKER_00",
              text: "Hej från lektionen.",
              language: "sv",
              confidence: 0.97,
            },
          ],
          language: { requested: "auto", detected: "sv", confidence: 0.98 },
          diarization: { status: "succeeded", mode_used: "known_speaker_count" },
          media: { duration_seconds: 3.2, chunk_count: 1, chunks: [] },
          metadata: {
            source: { sha256: "sha256:source" },
            normalized_audio_sha256: "sha256:normalized",
            runtime: { acceleration_used: "rocm" },
          },
          warnings: [],
          alignment: { status: "succeeded" },
        }),
      )
      .mockResolvedValueOnce(
        jsonResponse({ job: { job_id: "job_transcript_1", status: "canceled" } }),
      );

    await expect(
      client.getTranscriptJob({ correlationId: "corr_1", jobId: "job_transcript_1" }),
    ).resolves.toMatchObject({
      audioProgress: {
        percentComplete: 35,
        processedMediaSeconds: 42,
        totalMediaSeconds: 120,
      },
      stage: "transcribing",
      status: "running",
    });
    await expect(
      client.getTranscriptResult({ correlationId: "corr_1", jobId: "job_transcript_1" }),
    ).resolves.toMatchObject({
      conversion_metadata: { pipeline_used: "audio_to_transcript_bundle_v2" },
    });
    await expect(
      client.listTranscriptArtifacts({ correlationId: "corr_1", jobId: "job_transcript_1" }),
    ).resolves.toMatchObject({
      transcriptJsonArtifact: { artifact_key: "transcript_json", availability: "available" },
    });
    await expect(
      client.downloadTranscriptJson({ correlationId: "corr_1", jobId: "job_transcript_1" }),
    ).resolves.toMatchObject({
      segments: [{ speakerLabel: "SPEAKER_00", text: "Hej från lektionen." }],
      transcriptText: "Hej från lektionen.",
    });
    await expect(
      client.cancelTranscriptJob({ correlationId: "corr_1", jobId: "job_transcript_1" }),
    ).resolves.toMatchObject({ status: "canceled" });

    expect(fetcher.mock.calls.map((call) => call[0])).toEqual([
      "/sir-convert/v2/convert/jobs/job_transcript_1",
      "/sir-convert/v2/convert/jobs/job_transcript_1/result",
      "/sir-convert/v2/convert/jobs/job_transcript_1/artifacts",
      "/sir-convert/v2/convert/jobs/job_transcript_1/artifacts/transcript_json",
      "/sir-convert/v2/convert/jobs/job_transcript_1/cancel",
    ]);
    expect(fetchHeaders(fetcher, 4).get("X-CSRF-Token")).toBe("csrf-token");
  });

  it("rejects a successful result from a non-transcript pipeline", async () => {
    fetcher.mockResolvedValueOnce(
      jsonResponse({
        api_version: "v2",
        job_id: "job_transcript_1",
        result: {
          artifact: {
            filename: "converted.pdf",
            content_type: "application/pdf",
            sha256: "sha256:pdf",
            size_bytes: 512,
          },
          conversion_metadata: {
            pipeline_used: "html_to_pdf_v2",
            backend_used: "weasyprint",
            acceleration_used: "cpu",
            options_fingerprint: "pdf-options-fingerprint",
          },
        },
      }),
    );

    await expect(
      client.getTranscriptResult({ correlationId: "corr_1", jobId: "job_transcript_1" }),
    ).rejects.toMatchObject({
      code: "SIR_CONVERT_CONTRACT_DRIFT",
    } satisfies Partial<SirConvertGatewayError>);
  });

  it.each([
    ["missing JSON payload", null],
    [
      "empty transcript segments",
      validTranscriptJson({ transcript: { text: "Hej.", segments: [] } }),
    ],
    [
      "missing transcript text",
      validTranscriptJson({
        transcript: {
          segments: [
            {
              id: "seg_1",
              start_seconds: 0,
              end_seconds: 1,
              speaker_label: "SPEAKER_00",
              text: "Hej.",
            },
          ],
        },
      }),
    ],
    [
      "empty transcript text",
      validTranscriptJson({
        transcript: {
          text: "",
          segments: [
            {
              id: "seg_1",
              start_seconds: 0,
              end_seconds: 1,
              speaker_label: "SPEAKER_00",
              text: "Hej.",
            },
          ],
        },
      }),
    ],
    [
      "missing speaker labels",
      validTranscriptJson({
        transcript: {
          text: "Text without a speaker.",
          segments: [{ id: "seg_1", start_seconds: 0, end_seconds: 1, text: "Text" }],
        },
      }),
    ],
    [
      "diarization unavailable",
      validTranscriptJson({ diarization: { status: "unavailable" } }),
    ],
    ["diarization failed", validTranscriptJson({ diarization: { status: "failed" } })],
    [
      "diarization unavailable mode",
      validTranscriptJson({
        diarization: { status: "succeeded", mode_used: "diarization_unavailable" },
      }),
    ],
    ["alignment failed", validTranscriptJson({ alignment: { status: "failed" } })],
  ])("rejects false-success transcript JSON with %s", async (_caseName, payload) => {
    fetcher.mockResolvedValueOnce(
      jsonResponse(payload),
    );

    await expect(
      client.downloadTranscriptJson({ correlationId: "corr_1", jobId: "job_transcript_1" }),
    ).rejects.toMatchObject({
      code: "SIR_CONVERT_CONTRACT_DRIFT",
    } satisfies Partial<SirConvertGatewayError>);
  });
});
